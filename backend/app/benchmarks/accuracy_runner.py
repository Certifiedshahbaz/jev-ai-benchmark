import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from app.benchmarks.datasets import BENCHMARK_DATASET
from app.workflows.support_triage import QUESTIONS_MODE_B
from app.services.typesafe_service import typesafe_service
from app.services.llm_service import llm_service


class AccuracyBenchmarkRunner:
    """
    Executes curated benchmark dataset against both TypeSafe JEV System One
    and conventional LLM baseline (Groq) side-by-side using Mode B (15 questions).
    Measures ground-truth decision accuracy per field and overall.
    Provides live progress tracking, non-blocking background execution, and hard timeouts.
    """

    def __init__(self):
        self.progress: Dict[str, Any] = {
            "is_running": False,
            "current_case": 0,
            "total_cases": len(BENCHMARK_DATASET),
            "current_case_id": "",
            "percent": 0.0,
            "elapsed_seconds": 0.0,
            "phase": "idle",  # "idle" | "running" | "completed" | "error"
            "error": None,
            "latest_result": None,
        }
        self._bg_task: Optional[asyncio.Task] = None

    def get_progress(self) -> Dict[str, Any]:
        """Return a snapshot of current benchmark execution progress."""
        return dict(self.progress)

    def start_background_run(self, dataset: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Kick off the benchmark runner in an asynchronous background task.
        Allows instant return to the frontend to prevent long HTTP socket timeouts.
        """
        if self.progress.get("is_running") and self._bg_task and not self._bg_task.done():
            return {
                "status": "already_running",
                "message": "Benchmark is already currently executing.",
                "progress": self.get_progress(),
            }

        cases = dataset or BENCHMARK_DATASET
        self.progress.update({
            "is_running": True,
            "current_case": 0,
            "total_cases": len(cases),
            "current_case_id": "",
            "percent": 0.0,
            "elapsed_seconds": 0.0,
            "phase": "running",
            "error": None,
        })

        async def _runner_wrapper():
            try:
                await self.run_benchmark(dataset=cases)
            except Exception as e:
                self.progress["phase"] = "error"
                self.progress["is_running"] = False
                self.progress["error"] = str(e)

        self._bg_task = asyncio.create_task(_runner_wrapper())
        return {
            "status": "started",
            "message": "Accuracy benchmark started in background.",
            "progress": self.get_progress(),
        }

    @staticmethod
    def evaluate_field(
        field: str,
        expected_val: Any,
        answer_val: Any,
        ambiguous_multi_valid: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[bool, bool, Any, str]:
        """
        Evaluate single expected field against actual model answer.
        Returns: (is_correct, is_ambiguous_match, raw_actual_value, display_actual_string)
        """
        if answer_val is None:
            return False, False, None, "No answer returned"

        # Check if answer is a dict (like JEV answer object) or raw primitive (like LLM answer)
        ans_dict = answer_val if isinstance(answer_val, dict) else {}
        ans_type = ans_dict.get("type")

        # 1. Noul / Boolean (must check bool before int because bool subclasses int in Python)
        if ans_type == "noul" or "noul" in ans_dict or type(expected_val) is bool:
            actual_noul = ans_dict.get("noul") if "noul" in ans_dict else answer_val
            if actual_noul is not None:
                if isinstance(actual_noul, bool):
                    bool_pred = actual_noul
                    prob = 1.0 if bool_pred else 0.0
                elif isinstance(actual_noul, (int, float)):
                    prob = float(actual_noul)
                    bool_pred = (prob >= 0.5)
                elif isinstance(actual_noul, str):
                    bool_pred = actual_noul.strip().lower() in ("true", "yes", "1")
                    prob = 1.0 if bool_pred else 0.0
                else:
                    return False, False, None, f"Invalid noul: {actual_noul}"

                is_correct = (bool_pred == bool(expected_val))
                display = f"{'True' if bool_pred else 'False'} ({prob:.2f})"
                return is_correct, False, prob, display

        # 2. Score / Numeric
        if ans_type == "score" or "score" in ans_dict or (isinstance(expected_val, int) and type(expected_val) is not bool):
            actual_score = ans_dict.get("score") if "score" in ans_dict else answer_val
            if actual_score is not None:
                try:
                    num_val = float(actual_score)
                    diff = abs(num_val - float(expected_val))
                    is_correct = (diff <= 0.5)
                    display = f"{num_val:.2f} (diff: {diff:.2f})"
                    return is_correct, False, num_val, display
                except (ValueError, TypeError):
                    return False, False, None, f"Invalid score: {actual_score}"

        # 3. Choice / String Category
        if ans_type == "choice" or "choice" in ans_dict or isinstance(expected_val, str):
            actual_choice = ans_dict.get("choice") if "choice" in ans_dict else answer_val
            act_str = str(actual_choice).strip().lower() if actual_choice is not None else ""
            exp_str = str(expected_val).strip().lower()

            if act_str == exp_str:
                return True, False, actual_choice, str(actual_choice)

            # Check ambiguous_multi_valid
            if ambiguous_multi_valid and field in ambiguous_multi_valid:
                valid_options = [str(opt).strip().lower() for opt in ambiguous_multi_valid[field]]
                if act_str in valid_options:
                    # Valid under multi-valid ambiguity
                    return True, True, actual_choice, f"{actual_choice} (multi-valid: {', '.join(valid_options)})"

            return False, False, actual_choice, str(actual_choice)

        return False, False, None, "Unknown field format"

    async def run_benchmark(self, dataset: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute benchmark wrapped in a hard 3-minute timeout (180s) to prevent infinite hangs.
        """
        cases_to_run = dataset or BENCHMARK_DATASET
        total_cases = len(cases_to_run)

        self.progress.update({
            "is_running": True,
            "total_cases": total_cases,
            "phase": "running",
            "error": None,
        })

        try:
            # 180s hard timeout wrapper
            result = await asyncio.wait_for(self._run_internal(cases_to_run), timeout=180.0)
            self.progress.update({
                "phase": "completed",
                "is_running": False,
                "latest_result": result,
                "percent": 100.0,
            })
            return result
        except asyncio.TimeoutError:
            err_msg = "Accuracy benchmark timed out after 3 minutes (180s) due to upstream rate limits."
            self.progress.update({
                "phase": "error",
                "is_running": False,
                "error": err_msg,
            })
            raise TimeoutError(err_msg)
        except Exception as e:
            self.progress.update({
                "phase": "error",
                "is_running": False,
                "error": str(e),
            })
            raise e

    async def _run_internal(self, cases_to_run: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Internal sequential evaluation loop with pacing and live progress updates."""
        total_cases = len(cases_to_run)
        t0 = time.perf_counter()

        def make_engine_tracker():
            return {
                "field_stats": {},          # field -> {"correct": 0, "total": 0, "ambiguous": 0}
                "failed_case_ids": {},      # field -> [case_id, ...]
                "failed_cases": {},         # field -> [{"case_id": ..., ...}]
                "ambiguous_cases": {},      # field -> [{"case_id": ..., ...}]
                "duration_total_ms": 0.0,
            }

        jev_track = make_engine_tracker()
        llm_track = make_engine_tracker()
        detailed_cases: List[Dict[str, Any]] = []

        for idx, case in enumerate(cases_to_run, start=1):
            case_id = case["id"]
            category = case.get("category", "unknown")
            message = case["message"]
            context = case.get("customer_context", {})
            expected = case.get("expected", {})
            ambiguous_multi_valid = case.get("ambiguous_multi_valid", {})

            # Update live progress state
            self.progress["current_case"] = idx
            self.progress["current_case_id"] = case_id
            self.progress["percent"] = round((idx / total_cases) * 100, 1)
            self.progress["elapsed_seconds"] = round(time.perf_counter() - t0, 1)

            state = {
                "message": message,
                "customer_context": context,
            }

            # 1. Evaluate JEV System One
            jev_t0 = time.perf_counter()
            try:
                jev_res = await typesafe_service.evaluate(state=state, questions=QUESTIONS_MODE_B)
            except Exception as e:
                jev_res = e
            jev_ms = (time.perf_counter() - jev_t0) * 1000
            jev_track["duration_total_ms"] += jev_ms

            jev_answers = {} if isinstance(jev_res, Exception) else jev_res.get("answers", {})
            jev_err = str(jev_res) if isinstance(jev_res, Exception) else None

            # 2. Evaluate Conventional LLM baseline (Groq) with safety catch
            llm_t0 = time.perf_counter()
            try:
                llm_res = await llm_service.evaluate(state=state, questions=QUESTIONS_MODE_B)
            except Exception as e:
                llm_res = e
            llm_ms = (time.perf_counter() - llm_t0) * 1000
            llm_track["duration_total_ms"] += llm_ms

            llm_answers = {} if isinstance(llm_res, Exception) else llm_res.get("answers", {})
            llm_err = str(llm_res) if isinstance(llm_res, Exception) else None

            case_eval_record = {
                "id": case_id,
                "category": category,
                "message": message,
                "expected": expected,
                "ambiguous_multi_valid": ambiguous_multi_valid,
                "jev": {"evaluations": {}, "error": jev_err},
                "llm": {"evaluations": {}, "error": llm_err},
            }

            # Evaluate each expected field for both engines
            for field, exp_val in expected.items():
                for tracker, ans_dict, err, key in [
                    (jev_track, jev_answers, jev_err, "jev"),
                    (llm_track, llm_answers, llm_err, "llm"),
                ]:
                    f_stats = tracker["field_stats"]
                    if field not in f_stats:
                        f_stats[field] = {"correct": 0, "total": 0, "ambiguous": 0}
                        tracker["failed_case_ids"][field] = []
                        tracker["failed_cases"][field] = []
                        tracker["ambiguous_cases"][field] = []

                    f_stats[field]["total"] += 1

                    ans_obj = ans_dict.get(field)
                    if err:
                        is_corr = False
                        is_amb = False
                        raw_act = None
                        disp_act = f"Error: {err}"
                    else:
                        is_corr, is_amb, raw_act, disp_act = self.evaluate_field(
                            field, exp_val, ans_obj, ambiguous_multi_valid
                        )

                    if is_corr:
                        f_stats[field]["correct"] += 1
                        if is_amb:
                            f_stats[field]["ambiguous"] += 1
                            tracker["ambiguous_cases"][field].append({
                                "case_id": case_id,
                                "category": category,
                                "message": message,
                                "expected": exp_val,
                                "actual": disp_act,
                            })
                    else:
                        tracker["failed_case_ids"][field].append(case_id)
                        tracker["failed_cases"][field].append({
                            "case_id": case_id,
                            "category": category,
                            "message": message,
                            "expected": exp_val,
                            "actual": disp_act,
                        })

                    case_eval_record[key]["evaluations"][field] = {
                        "expected": exp_val,
                        "actual": disp_act,
                        "raw_actual": raw_act,
                        "is_correct": is_corr,
                        "is_ambiguous_match": is_amb,
                    }

            detailed_cases.append(case_eval_record)

            # Short polite delay (250ms) between calls to keep token bucket pacing steady
            await asyncio.sleep(0.25)

        total_duration = time.perf_counter() - t0

        def summarize_engine(tracker: Dict[str, Any], model_name: str) -> Dict[str, Any]:
            per_field = {}
            tot_correct = 0
            tot_evals = 0
            tot_amb = 0

            for f_name, f_data in tracker["field_stats"].items():
                c = f_data["correct"]
                t = f_data["total"]
                amb = f_data["ambiguous"]
                acc = round((c / t) * 100, 1) if t > 0 else 0.0
                per_field[f_name] = {
                    "field": f_name,
                    "correct": c,
                    "total": t,
                    "ambiguous_count": amb,
                    "accuracy": acc,
                }
                tot_correct += c
                tot_evals += t
                tot_amb += amb

            overall_acc = round((tot_correct / tot_evals) * 100, 1) if tot_evals > 0 else 0.0

            return {
                "model": model_name,
                "overall_accuracy": overall_acc,
                "total_evaluations": tot_evals,
                "total_correct": tot_correct,
                "ambiguous_matches": tot_amb,
                "duration_seconds": round(tracker["duration_total_ms"] / 1000.0, 2),
                "per_field_accuracy": per_field,
                "failed_case_ids": tracker["failed_case_ids"],
                "failed_cases": tracker["failed_cases"],
                "ambiguous_cases": tracker["ambiguous_cases"],
            }

        jev_summary = summarize_engine(jev_track, "jev-1.13.0")
        llm_summary = summarize_engine(llm_track, llm_service.model)

        # Save raw results JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        results_dir = project_root / "data" / "benchmark-results"
        results_dir.mkdir(parents=True, exist_ok=True)
        filename = f"accuracy_run_{timestamp}.json"
        filepath = results_dir / filename

        output_data = {
            "timestamp": timestamp,
            "total_cases": total_cases,
            "duration_seconds": round(total_duration, 2),
            "jev": jev_summary,
            "llm": llm_summary,
            "cases": detailed_cases,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        return {
            "status": "success",
            "total_cases": total_cases,
            "duration_seconds": round(total_duration, 2),
            "results_file": str(filepath),
            "jev": jev_summary,
            "llm": llm_summary,
        }

    def get_latest_benchmark(self) -> Optional[Dict[str, Any]]:
        """Return the most recent saved dual benchmark run if available."""
        # Check in-memory result first
        if self.progress.get("latest_result"):
            return self.progress["latest_result"]

        project_root = Path(__file__).resolve().parent.parent.parent.parent
        results_dir = project_root / "data" / "benchmark-results"
        if results_dir.exists():
            files = sorted(results_dir.glob("accuracy_run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if "jev" in data and "llm" in data and data.get("total_cases", 0) >= 40:
                            return {
                                "status": "success",
                                "total_cases": data.get("total_cases", 49),
                                "duration_seconds": data.get("duration_seconds", 0.0),
                                "results_file": str(f),
                                "jev": data["jev"],
                                "llm": data["llm"],
                            }
                except Exception:
                    continue

        # Fallback to bundled seed_benchmark.json for zero-config production deployments
        seed_path = Path(__file__).resolve().parent / "seed_benchmark.json"
        if seed_path.exists():
            try:
                with open(seed_path, "r", encoding="utf-8") as fp:
                    seed_data = json.load(fp)
                    if "jev" in seed_data and "llm" in seed_data:
                        return {
                            "status": "success",
                            "total_cases": seed_data.get("total_cases", 49),
                            "duration_seconds": seed_data.get("duration_seconds", 0.0),
                            "results_file": str(seed_path),
                            "jev": seed_data["jev"],
                            "llm": seed_data["llm"],
                        }
            except Exception:
                pass

        return None


accuracy_runner = AccuracyBenchmarkRunner()
