# Binder Showcase — TCR binder 设计成果可视化站

给合作者(生物老师)展示 CFM v3 从头生成、经 AlphaFold3 验证的 TCR binder 设计。
两种分享方式:
- **线上链接**(已部署):<https://xy-xuyang123.github.io/tcr-binder-showcase/> — 发链接即可访问,见 [§9 线上托管与更新 SOP](#9-线上托管与更新-sopgithub-pages)。
- **离线自包含**:双击 `index.html` 即可在浏览器打开,无需联网、无需安装。分享时把整个
  `binder_showcase/` 文件夹打包 zip 发出去即可。

---

## 1. 打开与分享

- **打开**:双击 `index.html`(Chrome / Edge 均可,需支持 WebGL,现代浏览器都行)。
- **分享**:整个文件夹打 zip → 发送。对方解压后双击 `index.html`。
- 不要单独发 `index.html`——它依赖 `assets/` 里的结构和图片。

> ⚠️ 必须保持文件夹结构完整。页面通过 `<script src>` / `<img src>` 加载本地资源
> (**不是** fetch/XHR,因为浏览器会拦截 `file://` 下的 XHR)。这也是为什么结构数据存成
> `cifs.js`(而非 .json)、PAE 存成外部 PNG。

---

## 2. 内容与范围

| 项 | 值 |
|---|---|
| 收录标准 | composite ipTM **≥ 0.7**(canonical "good binder") |
| 设计数 | **105 个独立设计**(107 个 AF3 job;2 个设计在 52_1/54_v1 两批各折叠一次,已按 id 去重保留高分那次) |
| 覆盖靶点 | **71 个 pMHC**(32 Class I + 39 Class II) |
| 每个设计 | 完整 AF3 原始产物:model_0 结构(`.cif`)+ PAE 矩阵 + per-residue pLDDT |

**汇总统计**(基于全部 2188 个 AF3 已评估候选,candidate-row 口径):
- 靶点覆盖:113/187 @0.6 · 71/187 @0.7 · 30/187 @0.8
- Class II 命中率 9.8% vs Class I 2.6%(≥0.7)
- 明星再设计案例:RPIIRPATL/b0801 经 v2 序列重设计从 0.254 → 0.904

> 注:覆盖率是**最新快照**(AF3 评估已从早期 66% 推进),高于 `resultv3/RESULTS.md`
> 正文里的旧数字(100/63/27)。以本站/JSON 为准。

---

## 3. 界面说明

- **右上角 `EN / 中文` 按钮**:一键切换全页中英文(含导航、图表、表格所有文字)。默认中文;
  给英语的老师看点一下切英文即可。
- **左栏**:71 个 pMHC 靶点,可按 `全部 / Class I / Class II` 筛选。每项显示肽/等位基因、
  类别、Class 标签、最佳 composite 分数条、以及该靶点的合格设计个数。
- **中列**:选中靶点后,列出其下设计的 pill(`#1 0.904`…),**按 composite ipTM 排序**。
- **主面板(AF3 官方式布局)**:
  - 左:交互式 3D 复合物。<span>青=设计 binder</span> / 灰青=MHC / <span>珊瑚=抗原肽</span>(棒状)。
    控制:`按角色上色 / 按 pLDDT 上色 / 肽棒状 / 旋转 / 复位`。拖动旋转、滚轮缩放。
  - 右:PAE 预测误差热图(绿色系,越绿=误差越低=越可信;链边界标注 Binder/MHC/Pep)+
    置信度格(composite、binder–peptide ipTM、overall ipTM、pTM、binder pLDDT、ranking)。
- 下方:汇总图表(靶点覆盖、composite 分布、Class I/II、类别命中、v1→v2 再设计前后)+ 生成成本表。

---

## 4. 指标定义

- **composite ipTM** = 0.8 × (binder–peptide ipTM) + 0.2 × (overall ipTM)。本项目排序主指标。
- **binder–peptide ipTM**:binder 与抗原肽之间的界面置信度(是否真的识别肽,而非只贴在 MHC 上)。
- **pLDDT**:AF3 per-residue 置信度(0–100)。"binder pLDDT" = 设计链的平均 pLDDT。3D 里
  按 pLDDT 上色时:蓝≥90 / 青70–90 / 黄50–70 / 橙<50。
- **PAE**:Predicted Aligned Error(Å),越低越可信;Binder×Peptide、Binder×MHC 块越深=相对定位越确定。
- **peptide_contact**:`on_peptide`(结合到肽,理想)/ `mislocated`(贴 MHC 但没抓到肽)/ `weak`。

---

## 5. 文件夹结构

```
binder_showcase/
├── index.html              应用本体(HTML + CSS + 交互 JS)。改界面直接编辑这个。
├── README.md               本文件
├── deploy_showcase.ps1     一键部署到 GitHub Pages 的脚本(见 §9)
├── assets/
│   ├── 3Dmol-min.js        3D 分子查看器库(来自 https://3dmol.org/build/3Dmol-min.js)
│   ├── data.js             window.DATA:指标、靶点分组、图表数据(~60KB)
│   ├── cifs.js             window.CIFS:105 个 model_0 结构文本(~24MB)
│   └── pae/<id>.png        105 张 PAE 热图(~2MB)
└── build/
    └── build_site.py       重新生成 assets/ 的脚本(见下)
```

---

## 6. 重新生成(有新 AF3 结果时)

```bash
# 默认阈值 0.7
python binder_showcase/build/build_site.py
# 轻量版(体积减半,适合发邮件):73 个设计 / 53 靶点
python binder_showcase/build/build_site.py 0.75
```

- 只重建 `assets/`(data.js / cifs.js / pae/*.png),**不改 `index.html`**(界面是手写的应用)。
- 脚本路径自动从自身位置推导,`ROOT` = `binder_showcase` 的上一级(即 `tcr-redesign/`)。
- `3Dmol-min.js` 缺失时会自动下载一次。
- 依赖:`numpy` `matplotlib` `Pillow`(**不需要 torch**)。

**要改界面/样式**:直接编辑 `index.html`(纯静态,改完刷新即可)。
**要换收录阈值**:改上面的命令行参数即可。

---

## 7. 数据来源

- `resultv3/candidates_metadata.json` — 2188 个 AF3 已评估候选的主表(composite、ipTM/pTM、类别等)。
- `resultv3/redesign_v2_comparison.json` — v1/v2 再设计前后配对(前后对比图)。
- `resultv3/hotspot/<category>/<抗原>_<allele>/af3/<run_tag>/<id>/` — AF3 Server 原始产物
  (`.cif` 结构 + `full_data_<best_seed>.json` 含 PAE / pLDDT)。

---

## 8. 技术要点 / 踩过的坑(下次省事)

1. **CIF 路径解析**:CSV/id → 文件夹需要归一化:小写、`-`/`.`→`_`,且 run_tag `54_v1` 的
   文件夹**和文件名都要加 `_v54` 后缀**。metadata 里的 `run_tag`/`candidate_path` 可能和实际
   af3 子目录对不上——所以 `build_site.py` 用**一次性遍历建 `fold_*_model_0.cif` 文件名索引**、
   按归一化 id 查表,而不是拼路径(拼路径只中 87/107,索引中 107/107)。
2. **PAE / pLDDT 来源**:机器没装 torch,所以从 `full_data_<best_seed>.json` 读
   (键:`pae`、`atom_plddts`、`atom_chain_ids`、`token_chain_ids`),不用 `pae.pt`。
3. **链角色判定**:peptide = 最短链;binder = 剩余链里长度最接近设计长度的;其余 = MHC。
   对 Class I(MHC 重链+β2m)和 Class II(α/β)都成立。
4. **去重**:同一设计可能在 52_1 和 54_v1 各折叠一次(分数不同)。按 id 去重,保留 composite 高的。
5. **`index.html` 必须以 `</script></body></html>` 正常闭合**——内联 `<script>` 不闭合会导致
   整块脚本**静默不执行且无报错**,页面所有动态内容空白。(踩过。)
6. **验证**:用 headless Chromium 实测(`--use-angle=swiftshader --allow-file-access-from-files`),
   确认 Class I/II 结构渲染、PAE 加载、无 console 报错。

---

## 9. 线上托管与更新 SOP(GitHub Pages)

站点已托管在 GitHub Pages,发链接即可访问,不用买域名、不用服务器。

**🔗 线上地址**:<https://xy-xuyang123.github.io/tcr-binder-showcase/>
**📦 部署仓库**:<https://github.com/xy-xuyang123/tcr-binder-showcase>(public)

### 9.1 访问范围(重要)

- 免费版 GitHub Pages 上线后**任何拿到链接的人都能看**;**无法**按邮箱/账号做白名单
  (那是 Enterprise 付费功能)。不主动发链接基本没人找得到,但技术上是公开的、可能被搜索引擎收录。
- 免费 Pages 要求仓库 public,所以 `data.js` / `cifs.js` 等**数据文件也公开可下载**。这是**未发表数据**,
  分享前请自行权衡。要真正按人限制,得改用 Cloudflare Pages + Access(邮箱白名单,另需配置)。

### 9.2 更新线上内容(日常 SOP)

改完 `binder_showcase/` 后,在 PowerShell 里跑一条命令即可同步到线上:

```powershell
# 直接推送当前 binder_showcase/ 内容(不重建 assets)
d:\tcr-redesign\binder_showcase\deploy_showcase.ps1

# 有新 AF3 结果时:先跑 build_site.py 重建 assets 再推送
d:\tcr-redesign\binder_showcase\deploy_showcase.ps1 -Rebuild
```

推送后**约 1 分钟**线上自动生效,链接不变。脚本做的事:
1. (`-Rebuild` 时)先跑 `build/build_site.py` 重建 `data.js / cifs.js / pae/*.png`;
2. 把 `binder_showcase/` 拷到临时目录 + 加 `.nojekyll`(关掉 Jekyll,纯静态站必需);
3. **单提交强制推送**(`git push -f`)到 `tcr-binder-showcase` 的 `main` 分支。

> **为什么强制推送?** 每次都用一个全新的单提交覆盖历史,仓库永远只有 1 个 commit,
> 24MB 的 `cifs.js` 不会随每次更新在 git 历史里越攒越大。代价是这个仓库没有版本历史
> (它只是 `binder_showcase/` 的发布镜像,源头始终以本地 `tcr-redesign/binder_showcase/` 为准)。

### 9.3 下线 / 撤回

想让链接立刻失效:

```powershell
# 方式 A:删掉整个部署仓库(最彻底,链接立即 404)
gh repo delete xy-xuyang123/tcr-binder-showcase --yes

# 方式 B:只关掉 Pages(保留仓库代码)
gh api -X DELETE repos/xy-xuyang123/tcr-binder-showcase/pages
```

### 9.4 一次性搭建过程(已完成,记录备查)

这套环境已经配好,以后**不用重来**;此处仅记录当时做了什么,便于换机/排错时复现:

1. **装 GitHub CLI**:winget 的 MSI 装法会卡在 UAC 提权(非交互无法弹窗),改用**便携版 zip**
   解压到 `C:\Users\admin\bin\gh_cli\`,并把 `...\gh_cli\bin` 加进用户 PATH。
2. **登录**:`gh auth login --web`(设备码流程),认证为 `xy-xuyang123`;`gh auth setup-git`
   让 git 用 gh 做凭证助手,https 推送免密。
3. **建仓库并推送**:`gh repo create xy-xuyang123/tcr-binder-showcase --public --source=. --push`。
4. **开 Pages**:`POST repos/.../pages`,source = `main` 分支 / 根目录;首次构建约 1–2 分钟。
5. **验证**:curl 实测 `index.html` / `3Dmol-min.js` / `data.js` / `cifs.js`(24MB)/ 抽查 PAE PNG 均 HTTP 200。

### 9.5 踩过的坑

- **`deploy_showcase.ps1` 必须存成 UTF-8 **带 BOM****。Windows PowerShell 5.1 会把无 BOM 的 UTF-8
  中文注释按系统 GBK 误读,吞掉字符导致括号不匹配、`Unexpected token '}'` 报错。存成 UTF-8 BOM 即可。
  (本 README 是 .md,无此问题,普通 UTF-8 即可。)
- **gh 路径兜底**:脚本里写死了 `C:\Users\admin\bin\gh_cli\bin` 作为兜底,只有当 `gh` 不在 PATH 时才追加;
  以后把 gh 正式装进系统 PATH 后这行会自动跳过。

---

*生成环境:单卡 RTX 4070 Laptop(8GB)生成 + AlphaFold3 Server 验证。*
