# AI 篮球 / 足球分析看板 — 用户行为与数据表现

基于根目录下多份 **AI 篮球分析看板**、**AI 足球分析看板** PDF 的数据分析项目，提供**定性 + 定量**分析看板。

**在线看板（可分享给同事）：**  
[https://ai-analysis-data-report-ujbyg6ywvtvxpsb26rp5jz.streamlit.app/](https://ai-analysis-data-report-ujbyg6ywvtvxpsb26rp5jz.streamlit.app/)

## 功能概览

- **定量分析**：使用总用户量（KPI）、功能使用高峰（近7天 / 近48小时）、每日使用次数（三线）、每日新增用户。
- **定性分析**：产品线对比、日活高峰与新增趋势的简短洞察。
- **数据来源**：从 PDF 抽取表格/文本；若 PDF 为图片型无文字，则使用与看板结构一致的模拟数据。

## 环境要求

- Python 3.9+
- 依赖见 `requirements.txt`

## 安装

```bash
cd "/Users/silas/Desktop/AI data analysis"
pip3 install -r requirements.txt
# 若系统只有 pip，可用: pip install -r requirements.txt
```

## 数据准备

1. **抽取 PDF**（可选，若 PDF 内含表格/文字则可抽取）  
   ```bash
   python scripts/extract_pdf_data.py
   ```
   - 输出：`data/raw/extracted_raw.csv`  
   - 若无法抽取到表格或文字，会生成 `data/raw/extraction_marker.txt`

2. **清洗与建模**（生成看板所用数据）  
   ```bash
   python scripts/clean_and_model.py
   ```
   - 若有可用抽取结果则进行清洗；否则生成与看板结构一致的模拟数据。  
   - 输出目录：`data/processed/`  
     - `kpi.csv`：总用户量等 KPI  
     - `peak_7d.csv`：近7天功能使用高峰  
     - `peak_48h.csv`：近48小时使用高峰  
     - `daily_usage.csv`：每日使用次数（平均/总次数/日活）  
     - `new_users.csv`：每日新增用户  

若未运行上述脚本，可先使用项目中已预生成的 `data/processed/` 数据（当前为模拟数据）。

## 启动看板

```bash
python3 -m streamlit run app.py
```

若已把 `streamlit` 加入 PATH，也可直接执行：`streamlit run app.py`。

**让同局域网同事访问**：加参数 `--server.address 0.0.0.0`，即：`python3 -m streamlit run app.py --server.address 0.0.0.0`，其他人用本机 IP:8501 访问。更多方式见下方「团队访问看板」。

在浏览器中打开提示的本地地址即可查看看板。侧边栏可切换产品线（篮球/足球），顶部为 KPI，下方为四块图表与定性洞察。

## 项目结构

```
.
├── app.py                    # Streamlit 看板入口
├── requirements.txt         # Python 依赖
├── .streamlit/
│   └── config.toml          # 看板主题与服务器配置（Cloud 部署时会用到）
├── scripts/
│   ├── extract_pdf_data.py   # PDF 数据抽取
│   ├── clean_and_model.py   # 清洗与建模（含模拟数据逻辑）
│   └── update_data.py       # 一键更新：抽取 + 清洗
├── data/
│   ├── raw/                  # 抽取原始结果
│   └── processed/            # 分析就绪数据（供看板使用，需提交以便 Cloud 展示）
├── 1-AI篮球分析看板(...).pdf  # 篮球看板 PDF（多份）
├── 2-AI足球分析看板(...).pdf  # 足球看板 PDF（多份）
└── README.md
```

## 数据说明

- **数据来源**：根目录下 `1-AI篮球分析看板*.pdf`、`2-AI足球分析看板*.pdf`。  
- 若 PDF 为图表截图（无嵌入表格/文字），抽取脚本会记录“无可用抽取”，清洗脚本将生成**模拟数据**，便于先跑通看板与迭代指标。  
- 数据更新时间：每次成功执行 `clean_and_model.py` 会覆盖 `data/processed/` 下文件。

## 如何更新数据（基于根目录 PDF）

看板展示的数据来自 `data/processed/` 下的 CSV。当根目录里的 PDF 有更新（或换了新一批看板导出）时，按下面流程刷新即可。

### 1. 更新 PDF

- 把新的或替换后的 **AI 篮球 / 足球分析看板 PDF** 放到项目**根目录**。
- 文件名需符合：`1-AI篮球分析看板*.pdf`、`2-AI足球分析看板*.pdf`（或含 Basketball / Soccer 的对应英文），脚本会按前缀区分篮球 / 足球。

### 2. 重新抽取 + 清洗

在项目根目录执行（二选一）：

**方式 A：分两步执行**

```bash
cd "/Users/silas/Desktop/AI data analysis"
python3 scripts/extract_pdf_data.py    # 从 PDF 抽取 → data/raw/
python3 scripts/clean_and_model.py     # 清洗/建模 → data/processed/
```

**方式 B：一键执行**（推荐）

```bash
cd "/Users/silas/Desktop/AI data analysis"
python3 scripts/update_data.py
```

`update_data.py` 会依次调用上述两个脚本，跑完即得到最新的 `data/processed/`。

### 3. 本地看板

若在本机用 `python3 -m streamlit run app.py` 看板，刷新浏览器即可看到新数据（Streamlit 会重新读 CSV）。

### 4. Streamlit Cloud 看板

若看板已部署在 [share.streamlit.io](https://share.streamlit.io)：

```bash
git add data/processed/
git commit -m "更新看板数据"
git push
```

推送后到 Streamlit Cloud 该应用页面点击 **Reboot app**（或等自动重新部署），线上看板会显示新数据。

### 说明

- **当前 PDF 多为图表/图片**：若 `extract_pdf_data.py` 抽不到表格或文字，会生成 `data/raw/extraction_marker.txt`，`clean_and_model.py` 会据此生成与看板结构一致的**模拟数据**，看板仍可正常展示。
- **若有导出的 CSV**：若能从报表系统或 BI 工具导出「总用户量、近7天高峰、近48小时、每日使用、每日新增」等 CSV，可按当前 `data/processed/` 下各文件的字段名与格式，直接覆盖对应 CSV，再执行上面第 3 或 4 步即可，无需再跑 PDF 抽取。

## 常见问题

- **`streamlit` 或 `pip` 找不到**：用 `python3 -m streamlit run app.py` 启动看板，用 `pip3 install -r requirements.txt` 或 `python3 -m pip install -r requirements.txt` 安装依赖。
- **看板提示“未找到数据”**：请先执行 `python3 scripts/clean_and_model.py` 生成 `data/processed/`。  
- **希望使用真实数据**：若后续有导出的 CSV/Excel（与当前 schema 一致），可替换或追加到 `data/processed/` 对应文件，或修改 `clean_and_model.py` 支持新数据源。

## 团队访问看板（按方式一：Streamlit Community Cloud）

按下面步骤部署后，团队任何人用浏览器打开一个**固定链接**即可访问，无需在本机跑程序。

### 步骤 1：把代码推到 GitHub

在项目根目录执行（若尚未初始化仓库）：

```bash
cd "/Users/silas/Desktop/AI data analysis"
git init
git add .
git commit -m "AI 分析看板 — 定性定量"
git branch -M main
git remote add origin https://github.com/siegzhong-maker/ai-analysis-data-report.git
git push -u origin main
```

若仓库已有内容，可直接 `git add .`、`git commit -m "..."`、`git push`。  
注意：`data/processed/` 需一并提交，看板才能在线显示数据；`.gitignore` 已排除 `*.pdf` 和 `.snapshots`，其余会正常提交。

**若 push 报错连到 ghproxy 超时**：说明本机 Git 把 GitHub 地址重写成了代理（`ghproxy.com`），代理连不上时会失败。任选一种方式即可：

- **改回直连 GitHub 再 push**（推荐）：  
  ```bash
  git remote set-url origin https://github.com/siegzhong-maker/ai-analysis-data-report.git
  git config --global --unset url.https://ghproxy.com/https://github.com/.insteadof
  git push -u origin main
  ```  
  之后若需继续用代理访问别的仓库，可再执行：  
  `git config --global url."https://ghproxy.com/https://github.com/.insteadOf" "https://github.com/"`

- **或用 SSH 推送**（不走代理）：  
  ```bash
  git remote set-url origin git@github.com:siegzhong-maker/ai-analysis-data-report.git
  git push -u origin main
  ```  
  需先在 GitHub 添加 SSH 公钥（Settings → SSH and GPG keys）。

### 步骤 2：在 Streamlit Cloud 部署

1. 打开 **[share.streamlit.io](https://share.streamlit.io)**，用 **GitHub 账号登录**。
2. 点击 **New app**。
3. 填写：
   - **Repository**：`siegzhong-maker/ai-analysis-data-report`
   - **Branch**：`main`
   - **Main file path**：`app.py`
4. 点击 **Deploy**，等待构建完成（约 1～3 分钟）。
5. 完成后页面上会显示应用地址，形如：`https://ai-analysis-data-report-xxx.streamlit.app`。

### 步骤 3：分享给团队

把下面**在线看板链接**发给同事，对方在浏览器打开即可查看看板，无需安装 Python 或运行任何命令。

**看板地址：**  
[https://ai-analysis-data-report-ujbyg6ywvtvxpsb26rp5jz.streamlit.app/](https://ai-analysis-data-report-ujbyg6ywvtvxpsb26rp5jz.streamlit.app/)

### 后续更新数据或代码

- **只更新数据**：本地更新 `data/processed/` 下 CSV 后，提交并推送；在 Streamlit Cloud 该应用页面点击 **Reboot app**（或等待自动重新部署），即可看到新数据。
- **更新代码**：推送后 Streamlit Cloud 会自动重新部署；若未触发，可手动点 **Reboot app**。

---

看板默认只在本机可访问（`http://localhost:8501`）。若不想用方式一，还可用下面几种方式。

### 方式二：同一局域网内访问

- 在一台电脑上执行：`python3 -m streamlit run app.py --server.address 0.0.0.0`
- 终端会提示 `Network URL: http://192.168.x.x:8501`（或类似）。记下这台电脑的**内网 IP**（如 `192.168.1.100`）。
- 同一 WiFi/局域网内的同事在浏览器打开 `http://192.168.1.100:8501` 即可访问。
- 适合临时开会、本机演示；关掉这台电脑或停止 Streamlit 后别人就访问不了。

### 方式三：临时外网链接（本机运行 + 穿透）

- 本机运行 `python3 -m streamlit run app.py` 后，用 [ngrok](https://ngrok.com) 或 [localtunnel](https://localtunnel.github.io/www/) 把本机 8501 端口暴露到公网，会得到一个临时 URL（如 `https://xxx.ngrok.io`），发给同事即可访问。
- 适合短期分享；链接通常有时效或每次重启会变。

### 方式四：内网服务器常驻

- 在团队共用的内网服务器（或一台长期开着的电脑）上安装依赖并运行：  
  `python3 -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501`
- 用 systemd / supervisor / 后台进程等方式保持常驻，把内网地址（如 `http://10.0.1.50:8501`）发给团队。
- 数据更新后替换服务器上的 `data/processed/` 并重启 Streamlit 即可。

按需选一种即可：**要省事、人人随时可访问**用方式一；**只在内网、不想要公网**用方式二或四；**临时给外网的人看一眼**用方式三。
