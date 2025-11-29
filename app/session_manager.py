import threading
import queue
import logging
import asyncio
from concurrent.futures import Future
from llm_session import Automator

logger = logging.getLogger("LLM-Manager")

class SessionManager:
    """
    Manages a single, persistent browser instance in a background thread.
    This ensures subsequent requests go to the SAME chat context.
    """
    def __init__(self):
        self._input_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        """
        Runs in a separate thread. Safe from asyncio conflicts.
        Keeps the 'bot' alive between requests.
        """
        bot = None
        creds = None
        
        logger.info("Worker Thread Started. Waiting for jobs...")

        while not self._stop_event.is_set():
            try:
                # Wait for a job (prompt or command)
                job = self._input_queue.get()
                
                type_ = job.get("type")
                payload = job.get("payload")
                future = job.get("future")
                
                # ---------------------------------------
                # COMMAND: PROCESS PROMPT
                # ---------------------------------------
                if type_ == "generate":
                    try:
                        # 1. Lazy Init: Start browser if not running
                        if bot is None:
                            logger.info("Starting new Browser Session...")
                            # Store creds for re-use if crash happens
                            creds = job.get("creds") 
                            bot = Automator(
                                provider="chatgpt",
                                headless=False,
                                credentials=creds
                            )
                        
                        # 2. Process
                        prompt = payload
                        logger.info("Sending prompt to existing session...")
                        
                        if isinstance(prompt, str):
                            result = bot.process_prompt(prompt)
                            mode = "single"
                        else:
                            result = bot.process_chain(prompt)
                            mode = "chain"
                            
                        # 3. Return Result
                        if not future.cancelled():
                            future.set_result({"status": "success", "mode": mode, "result": result})
                            
                    except Exception as e:
                        logger.error(f"Generation failed: {e}")
                        if not future.cancelled():
                            future.set_exception(e)

                # ---------------------------------------
                # COMMAND: RESET / DELETE SESSION
                # ---------------------------------------
                elif type_ == "reset":
                    logger.info("Reset command received. Closing Browser...")
                    if bot:
                        try:
                            bot.close()
                        except Exception as e:
                            logger.error(f"Error closing bot: {e}")
                        finally:
                            bot = None # Clear instance
                    
                    if not future.cancelled():
                        future.set_result(True)

                self._input_queue.task_done()

            except Exception as critical_e:
                logger.error(f"Critical Worker Error: {critical_e}")

    async def generate(self, prompt, creds):
        """Async wrapper to send job to thread"""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        # Bridge asyncio future to thread-safe logic
        thread_future = Future()
        
        def propagate_result(f):
            if f.cancelled():
                return
            exc = f.exception()
            if exc:
                loop.call_soon_threadsafe(future.set_exception, exc)
            else:
                loop.call_soon_threadsafe(future.set_result, f.result())

        thread_future.add_done_callback(propagate_result)
        
        self._input_queue.put({
            "type": "generate",
            "payload": prompt,
            "creds": creds,
            "future": thread_future
        })
        
        return await future

    async def reset(self):
        """Async wrapper to reset session"""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        thread_future = Future()

        def propagate_result(f):
            loop.call_soon_threadsafe(future.set_result, f.result())

        thread_future.add_done_callback(propagate_result)

        self._input_queue.put({
            "type": "reset",
            "payload": None,
            "future": thread_future
        })
        
        return await future
