import datetime
import pandas as pd
import re
import uvicorn
import os

from fastapi import FastAPI, UploadFile, Form
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from sklearn.ensemble import RandomForestRegressor as RF

app = FastAPI()
app.mount("/static", StaticFiles(directory="dist"), name="dist")

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


class FilePath(BaseModel):
    filepath: str


class FitRF(BaseModel):
    filepath: str
    target_filepath: str
    target_X_columns: list
    x_columns: list
    y_columns: list


@app.get("/shows")
def api_get_files():
    return get_files('files')


def get_files(filepath):
    file_name = filepath.split("/")[-1]
    res = {"path": filepath, "name": file_name}
    if os.path.isfile(filepath):
        return res
    children = []
    dirs = os.listdir(filepath)
    for val in dirs:
        children.append(get_files(filepath + "/" + val))
    res.update(dict(children=children))
    return res


def judge_filename_ava(filename):
    if re.match(r".*?demo\.xls$", filename):
        return False
    return True


@app.post("/upload_file")
async def upload_fie(file: UploadFile, filepath: str = Form()):
    filename = file.filename
    if not file:
        return {"type": "error", "message": "没有发送文件"}
    if not judge_filename_ava(filename):
        return {"type": "error", "message": "文件名不要以demo.xls结尾"}
    if not re.search(r'\w+\.xls$', filename):
        return {"type": "error", "message": "请发送xls格式excel"}
    content = await file.read()
    res = {"type": "error", "message": "success"}
    if not judge_filename_ava(filename):
        filename = filename.replace("demo", datetime.datetime.now().strftime("%Y%m%d"))
        res.update(dict(filename=filename))
    with open(filepath + "/" + filename, "wb") as f:
        f.write(content)
    # df = pd.read_excel(content)
    # print(df.columns)
    return res


@app.post("/rm_file")
async def remove_fie(data: FilePath):
    filepath = data.filepath
    if os.path.isfile(filepath) and filepath.startswith("files/") and judge_filename_ava(filepath):
        os.remove(filepath)
        return {"type": "success", "message": "success"}
    return {"type": "error",  "message": "error", "filepath": filepath}


@app.post("/download")
def download_file(data: FilePath):
    return FileResponse(data.filepath)


@app.post("/show_columns")
def get_trains_columns(data: FilePath):
    df = pd.read_excel(data.filepath)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    return dict(columns=list(df.columns))


@app.post('/fit_rf')
def fit_random_forest(data: FitRF):
    try:
        filename = data.filepath.split("/")[-1]
        if set(data.x_columns)^set(data.target_X_columns):
            raise Exception("x_columns 和 target_X_columns 应该一致")
        df = pd.read_excel(data.filepath)
        x = df[data.x_columns]
        y = df[data.y_columns]
        rf = RF(max_depth=5)
        rf.fit(x, y)
        target = pd.read_excel(data.target_filepath)[data.x_columns]
        res = rf.predict(target)
        res_df = pd.DataFrame(res, columns=data.y_columns)
        res = pd.concat([target, res_df], join="outer", axis=1)
        res_filename = "files/results/result_of_{}".format(filename)
        res.to_excel(res_filename, index=False)
    except Exception as e:
        print(e.__str__())
        return {"type": "error", "message": e.__str__()}
    return {"type": "success", "message": "success,生成新文件{}".format(res_filename)}


if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8000, reload=True)
