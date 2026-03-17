"""
预留的HTTP API接口
后续可用于微信小程序等外部调用
"""

# 预留接口，后续用 FastAPI 实现
# 基本结构如下：

"""
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Beads Designer API", version="1.0.0")

@app.post("/api/v1/generate")
async def generate_pattern(
    image: UploadFile = File(...),
    grid_width: int = 52,
    grid_height: int = 52,
    palette_brand: str = "Perler",
    max_colors: int = 0,
    dithering: bool = False
):
    '''
    生成拼豆图纸
    接收图片和参数，返回PDF文件
    '''
    # TODO: 实现
    pass

@app.get("/api/v1/palettes")
async def get_palettes():
    '''获取可用色板列表'''
    pass

@app.get("/api/v1/palettes/{brand}")
async def get_palette_colors(brand: str):
    '''获取指定色板的颜色列表'''
    pass

@app.get("/api/v1/history")
async def get_history():
    '''获取历史记录'''
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""