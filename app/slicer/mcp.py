import threading
from mcp.server.fastmcp import FastMCP
import anyio
import requests

try:
    from qt import QObject, Signal
    class SignalEmitter(QObject):
        load_volume_signal = Signal(str, result={'success': bool})
        list_volumes_signal = Signal(result={'success': bool, 'volumes': list}) 
    is_in_slicer = True
except ImportError:
    is_in_slicer = False

class MCPServer:
    def __init__(self, port=6666):
        self.port = port
        self.mcp = FastMCP(name = "SlicerWebServer", port=port)
        self.thread = None
        self.running = False
        self._configure_tools()
        if is_in_slicer:
            self.signal_emitter = SignalEmitter()
            self.signal_emitter.load_volume_signal.connect(self._load_volume)
    
    def _load_volume(self, volume_path):
        """加载体视显微镜数据到3D Slicer"""
        try:
            # 在主线程中执行Slicer API调用
            import slicer
            slicer.util.loadVolume(volume_path)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _configure_tools(self):
        SLICER_WEB_SERVER_URL = "http://localhost:2016"
        @self.mcp.tool()
        def get_node_names():
            """获取当前3D Slicer中的节点名称"""
            url = f"{SLICER_WEB_SERVER_URL}/slicer/mrml"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                assert isinstance(data, list)
            except requests.RequestException as e:
                return {'success': False, 'error': str(e)}
            except AssertionError:
                return {'success': False, 'error': 'Invalid response format'}
            return {'success': True, 'nodes': data}


        # add below tools only if in Slicer environment
        if not is_in_slicer:
            return
        @self.mcp.tool()
        def load_volume(volume_file_path:str):
            """加载体视显微镜数据到3D Slicer"""
            try:
                # 在主线程中执行Slicer API调用
                result = self.signal_emitter.load_volume_signal.emit(volume_file_path)
                return result
            except Exception as e:
                return {'success': False, 'error': str(e)}
    
    def start(self):
        """在单独线程中启动MCP服务器"""
        self.running = True
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()
    
    def _run_server(self):
        """运行MCP服务器的线程函数"""
        try:
            self.mcp.run(transport="sse")
        except Exception as e:
            print(f"Error running MCP server: {e}")
    
    def stop(self):
        """停止MCP服务器"""
        self.running = False
        if self.thread:
            self.thread.join(0.1) # shutdown server
            self.thread = None


if __name__ == "__main__":
    port = 6666
    server = MCPServer(port=port)

    server.start() # run the server in a separate thread
    # server._run_server() # run the server in the main thread

    print(f"Server started, you can now attach to it on http://localhost:{port}/sse")
    while(True):
        line = input("Press Enter to stop the server...")
        if line == "":
            break
    server.stop()
    print("Server stopped")
    # curl -X POST -d '{"jsonrpc": "2.0", "method": "notifications/initialized"}'  http://localhost:6666/messages/?session_id=a5e3a326afc545d0b44b3437cf68e694
    # curl -X POST -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'  http://localhost:6666/messages/?session_id=e8a898b5092c4c66a78c1bdd3c6f2b9f