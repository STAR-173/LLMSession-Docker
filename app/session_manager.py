import threading
import queue
import logging
import asyncio
import os
import time
from concurrent.futures import Future
from typing import Dict, List
from llm_session import Automator

logger = logging.getLogger("LLM-Manager")

class ProviderWorker:
    """
    A dedicated worker for a specific provider.
    """
    def __init__(self, provider_name: str, creds: dict, base_path: str):
        self.provider_name = provider_name
        self.creds = creds
        # Isolation: /root/.local/share/LLMSession/<provider_name>
        self.session_path = os.path.join(base_path, provider_name)
        os.makedirs(self.session_path, exist_ok=True)
        
        self.input_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.bot = None
        
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name=f"Worker-{provider_name}")
        self.thread.start()

    def perform_initial_login(self):
        """
        Runs the startup check.
        If cookies exist: Fast check (Parallel friendly).
        If cookies missing: Full Login (Heavy).
        """
        logger.info(f"[{self.provider_name}] Starting Login Sequence...")
        try:
            temp_bot = Automator(
                provider=self.provider_name,
                headless=False,
                credentials=self.creds,
                session_path=self.session_path
            )
            
            logger.info(f"[{self.provider_name}] Login/Check Successful. Persisting session...")
            temp_bot.close()
            logger.info(f"[{self.provider_name}] Browser closed. Ready.")
            return True
            
        except Exception as e:
            logger.error(f"[{self.provider_name}] Login Failed: {e}")
            try:
                if 'temp_bot' in locals():
                    temp_bot.close()
            except:
                pass
            return False

    def _safe_close_bot(self):
        """Helper to safely close the bot and ensure reference is cleared."""
        if self.bot:
            try:
                logger.info(f"[{self.provider_name}] Closing browser instance...")
                self.bot.close()
            except Exception as e:
                logger.warning(f"[{self.provider_name}] Error closing browser: {e}")
            finally:
                self.bot = None

    def _worker_loop(self):
        while not self.stop_event.is_set():
            try:
                job = self.input_queue.get()
                job_type = job.get("type")
                payload = job.get("payload")
                future = job.get("future")

                if job_type == "generate":
                    try:
                        if self.bot is None:
                            logger.info(f"[{self.provider_name}] Waking up browser...")
                            self.bot = Automator(
                                provider=self.provider_name,
                                headless=False,
                                credentials=self.creds,
                                session_path=self.session_path
                            )

                        logger.info(f"[{self.provider_name}] Processing prompt...")
                        if isinstance(payload, str):
                            result = self.bot.process_prompt(payload)
                            mode = "single"
                        else:
                            result = self.bot.process_chain(payload)
                            mode = "chain"
                        
                        if not future.cancelled():
                            future.set_result({"status": "success", "mode": mode, "result": result})
                            
                    except Exception as e:
                        logger.error(f"[{self.provider_name}] Generation Error: {e}")
                        # CRITICAL FIX: If generation fails, the browser state is likely corrupted or timed out.
                        # We must close it so the next request starts fresh.
                        self._safe_close_bot()
                        
                        if not future.cancelled():
                            future.set_exception(e)

                elif job_type == "reset":
                    # Force close the session
                    self._safe_close_bot()
                    if not future.cancelled():
                        future.set_result(True)

                self.input_queue.task_done()
            except Exception as e:
                logger.error(f"[{self.provider_name}] Loop Error: {e}")

class SessionManager:
    """
    Manages the BATCHED startup and routing of providers.
    """
    def __init__(self):
        self.workers: Dict[str, ProviderWorker] = {}
        self.base_dir = "/root/.local/share/LLMSession"

    async def start_providers(self):
        """
        Batch 1: ChatGPT + AIStudio (Parallel)
        Batch 2: Claude (Sequential)
        """
        email = os.environ.get("GOOGLE_EMAIL")
        password = os.environ.get("GOOGLE_PASSWORD")

        if not email or not password:
            logger.error("CRITICAL: GOOGLE_EMAIL or GOOGLE_PASSWORD not set.")
            return

        creds = {"email": email, "password": password, "method": "google"}
        
        # 1. Initialize Workers
        providers_list = ["chatgpt", "aistudio", "claude"]
        for p in providers_list:
            self.workers[p] = ProviderWorker(p, creds, self.base_dir)

        # ---------------------------------------------------------
        # BATCH 1: ChatGPT & AIStudio
        # ---------------------------------------------------------
        batch_1_names = ["chatgpt", "aistudio"]
        logger.info(f"--- Starting Batch 1: {', '.join(batch_1_names)} ---")
        
        tasks_1 = []
        for name in batch_1_names:
            worker = self.workers[name]
            tasks_1.append(asyncio.to_thread(worker.perform_initial_login))
        
        results_1 = await asyncio.gather(*tasks_1, return_exceptions=True)
        
        for name, res in zip(batch_1_names, results_1):
            status = "READY" if res is True else "FAILED"
            logger.info(f"--- {name}: {status} ---")

        logger.info("Batch 1 complete. Cooling down Xvfb...")
        await asyncio.sleep(2)

        # ---------------------------------------------------------
        # BATCH 2: Claude
        # ---------------------------------------------------------
        batch_2_names = ["claude"]
        logger.info(f"--- Starting Batch 2: {', '.join(batch_2_names)} ---")
        
        tasks_2 = []
        for name in batch_2_names:
            worker = self.workers[name]
            tasks_2.append(asyncio.to_thread(worker.perform_initial_login))
            
        results_2 = await asyncio.gather(*tasks_2, return_exceptions=True)

        for name, res in zip(batch_2_names, results_2):
            status = "READY" if res is True else "FAILED"
            logger.info(f"--- {name}: {status} ---")

        logger.info("All initialization batches finished.")

    async def generate(self, provider: str, prompt):
        if provider not in self.workers:
            raise ValueError(f"Provider '{provider}' is not active.")
        
        worker = self.workers[provider]
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        thread_future = Future()

        def propagate_result(f):
            if f.cancelled(): return
            exc = f.exception()
            if exc:
                loop.call_soon_threadsafe(future.set_exception, exc)
            else:
                loop.call_soon_threadsafe(future.set_result, f.result())

        thread_future.add_done_callback(propagate_result)

        worker.input_queue.put({
            "type": "generate",
            "payload": prompt,
            "future": thread_future
        })
        
        return await future

    async def reset_provider(self, provider: str):
        if provider not in self.workers:
            raise ValueError(f"Provider '{provider}' not found.")
        
        worker = self.workers[provider]
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        thread_future = Future()
        
        def propagate_result(f):
             loop.call_soon_threadsafe(future.set_result, f.result())
        
        thread_future.add_done_callback(propagate_result)

        worker.input_queue.put({
            "type": "reset",
            "future": thread_future
        })
        
        return await future