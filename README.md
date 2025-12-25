# agent study project
目录结构
```
app/
├── agent/
│   ├── core.py
│   ├── prompts.py
│   ├── schemas.py
│   ├── tools.py
├── infra/
│   ├── logging.py
├── main.py
```


## 运行项目
uvicorn app.main:app --reload --port 8000