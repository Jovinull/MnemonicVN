# api_client.rpy
# Cliente HTTP para a VividNexus API. Usa urllib (stdlib) para evitar
# dependência externa. Chamadas longas (Qwen pode levar segundos) NÃO devem
# bloquear o loop principal do Ren'Py — para isso existe `AsyncRequest`,
# uma handle simples cujo `done` é polled em loop por uma label que chama
# `renpy.pause(0.1, hard=True)` para manter a UI viva.

init -10 python:
    import json
    import threading
    try:
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError
    except ImportError:  # Ren'Py legado (Py2)
        from urllib2 import Request, urlopen, URLError, HTTPError

    API_BASE_URL = "http://localhost:8000"
    API_TIMEOUT_SECONDS = 60   # Qwen local pode demorar; folga generosa

    # ============================================================
    # Handle assíncrona — encapsula uma thread daemon
    # ============================================================
    class AsyncRequest(object):
        """Estado compartilhado entre a thread worker e o loop principal.

        O loop do Ren'Py consulta `done` (e opcionalmente `elapsed_ms()` para
        animar o indicador). Quando a thread termina, `result` ou `error`
        está preenchido e `renpy.restart_interaction()` é chamado para
        acordar imediatamente um `pause` em curso.
        """

        def __init__(self, label="api"):
            self.label = label
            self.result = None
            self.error = None
            self.done = False
            self._started_at = None
            self._lock = threading.Lock()

        def _set(self, result=None, error=None):
            with self._lock:
                self.result = result
                self.error = error
                self.done = True
            try:
                # Acorda qualquer `renpy.pause(..., hard=True)` em curso.
                renpy.restart_interaction()
            except Exception:
                pass

        def start(self, fn, *args, **kwargs):
            import time as _time
            self._started_at = _time.time()

            def _run():
                try:
                    self._set(result=fn(*args, **kwargs))
                except Exception as exc:
                    self._set(error=str(exc))

            t = threading.Thread(target=_run, name="api-" + self.label)
            t.daemon = True
            t.start()
            return self

        def elapsed_ms(self):
            import time as _time
            if self._started_at is None:
                return 0
            return int((_time.time() - self._started_at) * 1000)


    # ============================================================
    # Cliente HTTP
    # ============================================================
    class APIClient(object):
        """Cliente HTTP minimalista. Cada método tem versão sync (`x`) e
        versão async (`x_async`) que devolve um `AsyncRequest`."""

        def __init__(self, base_url=API_BASE_URL, timeout=API_TIMEOUT_SECONDS):
            self.base_url = base_url.rstrip("/")
            self.timeout = timeout

        # ---- core sync ----
        def _request(self, method, path, payload=None):
            url = self.base_url + path
            data = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

            req = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body) if body else {}
            except HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")
                raise RuntimeError("HTTP {0} em {1}: {2}".format(e.code, path, detail))
            except URLError as e:
                raise RuntimeError("Falha de rede em {0}: {1}".format(path, e.reason))

        # ---- endpoints sync ----
        def health(self):
            return self._request("GET", "/health")

        def interact(self, npc_id, player_input, contexto_extra=None):
            return self._request("POST", "/interact", {
                "npc_id": npc_id,
                "player_input": player_input,
                "contexto_extra": contexto_extra,
            })

        def world_tick(self, delta_ticks=1):
            return self._request("POST", "/world-tick", {"delta_ticks": delta_ticks})

        def get_npc_status(self, npc_id):
            return self._request("GET", "/get-npc-status/{0}".format(npc_id))

        def list_locais(self):
            return self._request("GET", "/locais")

        def npcs_no_local(self, local_id):
            return self._request("GET", "/locais/{0}/npcs".format(local_id))

        def get_world_status(self):
            return self._request("GET", "/world-status")

        def observe(self, local_id, jogador_id=1):
            return self._request("POST", "/observe", {
                "local_id": local_id,
                "jogador_id": jogador_id,
            })

        # ---- endpoints async ----
        def interact_async(self, npc_id, player_input, contexto_extra=None):
            handle = AsyncRequest(label="interact:{0}".format(npc_id))
            return handle.start(self.interact, npc_id, player_input, contexto_extra)

        def world_tick_async(self, delta_ticks=1):
            handle = AsyncRequest(label="world-tick")
            return handle.start(self.world_tick, delta_ticks)

        def observe_async(self, local_id, jogador_id=1):
            handle = AsyncRequest(label="observe:{0}".format(local_id))
            return handle.start(self.observe, local_id, jogador_id)


    api = APIClient()


    def parse_interact_response(handle):
        """Helper: traduz um AsyncRequest concluído em (fala, novo_humor, acao).
        Em caso de erro, devolve uma fala de fallback com a mensagem do erro."""
        if not handle.done:
            return ("(carregando...)", None, None)
        if handle.error:
            return ("[erro de API: {0}]".format(handle.error), None, None)
        data = handle.result or {}
        return (
            data.get("fala", "..."),
            data.get("novo_humor"),
            data.get("acao"),
        )


    def parse_observe_response(handle):
        """Helper: extrai o campo `descricao` da resposta de /observe.
        Em caso de erro de rede ou descrição vazia, devolve um fallback curto."""
        if not handle.done:
            return "(observando...)"
        if handle.error:
            return "[erro ao observar: {0}]".format(handle.error)
        data = handle.result or {}
        descricao = (data.get("descricao") or "").strip()
        return descricao or "Você olha em volta. Nada chama atenção."


    # Mantido por compatibilidade — código novo deve usar `interact_async`.
    def call_npc_blocking(npc_id, player_input, contexto_extra=None):
        try:
            data = api.interact(npc_id, player_input, contexto_extra)
            return (data.get("fala", "..."), data.get("novo_humor"), data.get("acao"))
        except Exception as exc:
            return ("[erro de API: {0}]".format(exc), None, None)
