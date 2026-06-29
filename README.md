# 卫浴行业数据观察智库

基于 Streamlit 的中国海关进出口数据智能化分析平台。

## 项目结构

```
├── app.py                    # 主应用（已支持内置数据）
├── prepare_default_data.py   # 生成内置数据的脚本
├── requirements.txt
├── data/                     # 内置数据目录（生成后自动创建）
│   ├── default_6910.parquet  # 6910 编码默认数据
│   └── 区域映射表.xlsx       # 区域映射表
├── 区域映射表.xlsx           # 放在根目录或 data/
├── raw_data/                 # 放原始Excel用于生成内置数据
└── README.md
```

## 使用步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 准备内置数据（推荐）
1. 把你的 6910 年度 Excel 文件放入 `raw_data/` 文件夹
2. 运行：
   ```bash
   python prepare_default_data.py
   ```
3. 生成 `data/default_6910.parquet`

### 3. 运行网站
```bash
streamlit run app.py
```

打开浏览器即可看到内置数据，无需上传。

### 4. 自定义数据
关闭侧边栏“使用内置默认数据”开关，即可上传自己的文件。

## 部署到 Streamlit Cloud
1. Fork 到 GitHub
2. 在 Streamlit Cloud 连接仓库
3. 把 `data/` 目录和 parquet 文件一起提交

**注意**：首次部署需确保 `data/default_6910.parquet` 已存在。
