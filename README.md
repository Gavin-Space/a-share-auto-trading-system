# a-share-auto-trading-system

自动化 A 股交易系统骨架（Python）。

目标：提供回放器、事件驱动策略框架、模拟执行器与 Web 仪表盘起点，后续对接国金证券 API（待你提供文档/凭证）。

主要目录结构：
- app/                  FastAPI 后端（WebSocket + 控制 API）
- trading/              策略、回放器与执行器模块
- frontend/             简单的 Dashboard 静态页面（通过 WebSocket 显示行情与交易事件）
- config.yaml           可修改的运行配置（初始资金、模式）
- Dockerfile / docker-compose.yml

快速开始（本地）:
1. 安装依赖: pip install -r requirements.txt
2. 运行服务: uvicorn app.main:app --reload
3. 打开仪表盘: http://localhost:8000/dashboard
4. 使用 POST /start_replay 提供历史 CSV 路径以开始回放

注意：当前版本使用本地回放与模拟（paper）执行；真实对接国金证券需提供 API 文档与沙盒凭证。
