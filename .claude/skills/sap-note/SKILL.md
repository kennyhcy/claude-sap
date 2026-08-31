---
name: sap-note
description: 读取 SAP Note / KBA 全文。调用本 skill 后必须先用 Read 把本 SKILL.md 全文读完（正文有脚本路径、缓存机制、禁止项，只看 description 不够），并必须用同目录 get_sapnote.ps1 脚本抓取——禁止用 WebFetch 或自拼 Edge/curl 命令（SAP session cookie 是 HttpOnly，只有脚本里的独立 Edge profile 才带得上）。当用户要求"看/查/读一下某个 SAP Note 编号"（如"读 note 2743317"）时使用。
---

# SAP Note 读取

> ## 🔴 调用本 skill 前必读（最高优先级）
>
> **在执行任何抓取动作之前，必须先用 Read 工具把本 SKILL.md 从头读到尾。** 不要只看 frontmatter 的 description 就动手——description 只是触发提示，真正的工作流程、路径、脚本调用形式、缓存机制、禁止项全在正文里。
>
> 读完之后，严格遵守下面三条强制规范：
>
> 1. **必须用本 skill 同目录的 `get_sapnote.ps1` 脚本抓取，禁止自拼命令。** 不得用 `WebFetch`、不得自己拼 `msedge --headless --dump-dom`、不得用 `curl`/`Invoke-WebRequest`——这些统统抓不到 SAP 的 HttpOnly session cookie，只会浪费时间还可能误导用户。脚本已经把这些坑全处理好了（独立 Edge profile、`<pre>` 提取、实体解码、JSON 校验、登录态过期自动开窗），用它就够了。
> 2. **先查缓存，命中就不调脚本。** 把编号补零到 10 位（`2743317` → `0002743317.json`），检查 `sap-notes/<编号>.json` 是否已存在；存在就直接 Read 它解析，**不调脚本、不走网络**。
> 3. **路径以本 skill 文件所在目录为准。** 本 skill 在**项目目录**的 `.claude/skills/sap-note/` 下（不是 `~/.claude/skills`）。脚本相对项目根的路径是 `.claude/skills/sap-note/get_sapnote.ps1`。别去用户主目录的 `.claude/skills` 下找——那里没有。

读取指定编号的 SAP Note / KBA，拿到其 JSON 内容并给出摘要。

底层工具是同目录下的 `get_sapnote.ps1`：它用 headless Edge（一个独立的 profile 目录存登录态）访问 SAP Note API，把响应存成 `sap-notes/<编号>.json`（编号补零到 10 位）。它**不是**普通的 HTTP 请求——SAP 的 session cookie 是 HttpOnly，只有浏览器进程自己请求才能带上，所以必须走 Edge，且必须走这个脚本（它已经处理好 profile 隔离、DOM 提取、实体解码、JSON 校验、登录态过期开窗等所有细节）。

## 这个 skill 是自包含的

整个 `.claude/skills/sap-note/` 文件夹是自包含的，所有东西都跟着 skill 走，**不依赖任何当前项目特有的东西**：

- 脚本本身：`get_sapnote.ps1`（同目录）
- 缓存目录：`sap-notes/`（同目录，脚本启动时自动创建）
- Edge profile 目录：由脚本管理，位于用户 AppData 下（`%LOCALAPPDATA%\SAPNoteEdgeProfile`），与用户日常 Edge 隔离，脚本自动创建维护，**不需要用户手动配置**

将来要搬到别的项目，**原样拷贝整个 `.claude/skills/sap-note/` 文件夹即可，无需改动任何路径或配置**。

### 前置依赖

- Windows 操作系统
- PowerShell（Windows 自带即可）
- Microsoft Edge 浏览器（脚本会自动在常见安装路径下找 `msedge.exe`）

### 首次使用 / 换机器使用

登录态是跟**机器 + Edge profile** 绑定的。首次使用、换机器、或 profile 目录丢失时，脚本会自动跳过 headless 尝试，直接开一个 Edge 窗口引导用户登录 SAP 一次（登录态存进上面那个独立 profile 目录，之后复用）。用户无需手动配置 profile。

## 缓存机制

已抓过的 note JSON 都缓存在同目录下的 `sap-notes/` 子文件夹里。查 note 时**先看缓存**：把编号补零到 10 位拼成文件名（如 `2743317` → `0002743317.json`，脚本 `Format-NoteNumber` 也是这么补零的），若 `sap-notes/<编号>.json` 已存在，直接用 Read 工具读它解析，**不调用脚本**、不走网络。只有缓存里没有时才抓取。

**缓存上限：100 条。** 抓取新 note 落盘后，若 `sap-notes/` 里的 note 文件数超过 100，删掉最早抓取的那几条，使数量回到 ≤ 100。"最早"按文件修改时间（mtime）判断：缓存文件只被读取、从不重写，已缓存 note 也不会被重新抓取，所以 mtime 就等于当初抓取时间，mtime 最旧的就是"最开始的几条"。这是 skill 在抓取后用 Bash 自己做的清理动作，**不是脚本行为**——脚本不改、不负责清缓存。

## 调用方式

脚本路径（相对项目根）：`.claude/skills/sap-note/get_sapnote.ps1`
调用形式（接受**一个或多个**编号作为位置参数，脚本自动补零到 10 位）：
```
powershell -ExecutionPolicy Bypass -File ".claude/skills/sap-note/get_sapnote.ps1" <编号> [<编号> ...]
```
- 单条：`... get_sapnote.ps1 2743317`
- 批量：`... get_sapnote.ps1 3152102 3570335 2743317`

批量时脚本**内部串行**抓取、复用同一个 Edge profile，session 过期时**只弹一次登录窗**，登录关窗后继续抓剩余的；已缓存的编号自动跳过（不走网络）。末尾打印汇总（OK / 缓存 / 失败），全成功 exit 0、有失败 exit 1。

### 🔴 绝对不要并发跑多个脚本实例

所有抓取实例共用**同一个** Edge profile 目录（`%LOCALAPPDATA%\SAPNoteEdgeProfile`），而 Chromium **禁止两个进程同时占用一个 profile**。并发起多个 `get_sapnote.ps1` 会互锁；更糟的是，当某个实例的 headless 抓取因 profile 被占而返回 `error` 时，它的清残留逻辑会 `Stop-Process -Force` 杀掉**所有**用该 profile 的 Edge，**包括另一个实例正在用的登录窗口**。被强杀的窗口没走完整关闭流程，session cookie 没干净落盘，于是抓取报 500。

要"并行获取多个 note"，**正确做法是把多个编号传给一次调用**（脚本内部串行、登录只一次），而不是并发起多个进程。同一时刻只允许有一个 `get_sapnote.ps1` 在跑。

**这是唯一的抓取入口。** 不要绕开它自己拼 Edge 命令或用 WebFetch——SAP 的 HttpOnly session cookie 只有走脚本里那个独立 Edge profile 才能带上，其它方式一律抓不到正文（只会拿到登录页 / SPA 空壳 / Internal Server Error）。

脚本流程：

1. 先用 headless Edge 抓取。
2. 若 profile 被残留 Edge 占用，清理后重试一次。
3. 若会话过期（login redirect），脚本开一个**有窗口的** Edge 落在 `me.sap.com`，等用户在里面登录 SAP。**登录窗口开着期间，脚本完全不碰 profile**——只通过 WMI 数 Edge 进程，纯被动等用户关窗。这是因为 Chromium 不允许两个进程共用同一 profile 目录：早期版本在登录期间每 5 秒跑一个 headless Edge 去探测登录是否完成，会反复抢 profile 锁、触发 hand-off，导致前台登录窗口卡死、按钮点不动；该 headless 探测后来也证明对 SAML SPA 主页不可靠（会在登录成功后误判「未登录」、阻断抓取），已彻底移除。现在改成：用户在窗口里完成登录后**自己关掉那个 Edge 窗口**，脚本检测到窗口关闭（profile 解锁、cookie 已随 Edge 关闭流程干净落盘）后，直接用 `Try-FetchNote`（内部已 3 次重试 + 严格 JSON 校验）抓取 note，session 有效性交给其返回值（ok/login/error）判断，login 则提示重跑。让 Edge 走完整的关闭流程把 HttpOnly session cookie 落盘到 profile，是为了避免抓取报 login redirect。

skill 这边只要告诉用户：在弹出的 Edge 窗口里登录 SAP，确认登录成功后**自己关掉那个 Edge 窗口**，脚本检测到窗口关闭后会自动继续抓取。

## 工作流程（skill 内）

1. **用户给编号**（如"读 note 2743317"）。编号可以是数字，脚本会自动补零到 10 位。
2. **先查缓存**：把编号补零到 10 位拼文件名（`2743317` → `0002743317.json`），检查 `.claude/skills/sap-note/sap-notes/<编号>.json` 是否已存在。
   - **已存在**：直接用 Read 工具读这个缓存文件解析，**不调用脚本、不走网络**，跳到第 3 步。
   - **不存在**：继续第 2b 步抓取。
2b. **抓取**（仅缓存未命中时）。单个或多个未命中编号一起传给一次调用，脚本内部串行抓取、登录只一次：
   ```
   powershell -ExecutionPolicy Bypass -File ".claude/skills/sap-note/get_sapnote.ps1" 2743317
   powershell -ExecutionPolicy Bypass -File ".claude/skills/sap-note/get_sapnote.ps1" 3152102 3570335
   ```
   - 成功：脚本把每条 JSON 存进 `sap-notes/<编号>.json`，末尾打印 `Fetched OK / From cache / Failed` 汇总。
   - 会话过期：脚本会自动开 Edge 窗口让用户登录。skill 只需提示用户：**在弹出的 Edge 窗口里登录 SAP，确认登录成功后自己关掉那个窗口，脚本检测到你关窗后会自动继续抓取**。脚本不会代为关窗——这是为了让 Edge 把登录 cookie 干净落盘。skill 不用插手脚本逻辑。
   - 其它 error：把脚本返回的 msg 告诉用户。
   - **禁止并发起多个 `get_sapnote.ps1` 进程**：它们共用一个 Edge profile 会互锁，还会互杀登录窗口导致 500。多 note 一律走单次批量调用。
2c. **抓取后清缓存（仅当本步 2b 有新 note 落盘时执行；全部命中缓存、没抓新 note 则跳过）**：抓取可能给 `sap-notes/` 新增了文件，此时检查缓存总数，超过 100 就删最旧的直到 ≤ 100。用 Bash（cwd 为项目根）：
   ```bash
   d=".claude/skills/sap-note/sap-notes"
   n=$(ls -1 "$d"/*.json 2>/dev/null | wc -l)
   if [ "$n" -gt 100 ]; then
     ls -t "$d"/*.json | tail -n +101 | xargs -r rm -f
     echo "trimmed cache: $n -> <=100"
   fi
   ```
   `ls -t` 按 mtime 从新到旧列出，`tail -n +101` 取第 101 条及之后（即超出最新 100 条的最旧部分）交给 `rm` 删除。文件名是补零编号、路径无空格，`xargs` 安全。新抓的 note mtime 最新，本轮不会被删。这是 skill 的清理动作，**不是脚本行为**。
3. **读取 JSON 文件**（优先从缓存读；缓存没有才抓、抓完再读——路径在脚本输出里，用 Read 工具），解析关键字段：
   - `Response.SAPNote.Header`：Number、Type、Title、Component、Status、ReleasedOn、Version
   - `Response.SAPNote.LongText.value`：正文（HTML），即 Symptom / Environment / Resolution / See Also / Keywords 等
   - `Response.SAPNote.Attributes`、`References`、`Validity`：属性、关联 Note、适用产品
4. **用中文给出摘要**：标题、类型、组件、解决什么问题、关键解决步骤、关联 Note。HTML 正文里有 `<img>` 引用的是 SAP 内部图，看不了，文字部分正常读即可。
5. 抓到的 `.json` 留在 `sap-notes/` 子文件夹（`.claude/skills/sap-note/sap-notes/<编号>.json`），**这就是缓存**，下次再查同一个 note 直接复用、不再抓网络，**不要外传**。

## 注意与约束

- 脚本和输出文件仅本地查看，勿分发。
- 抓取依赖当前机器上已登录 SAP 的 Edge profile；换机器或 profile 丢失时要重新登录一次（脚本会自动开窗口引导）。
- 登录态过期时，脚本会开 Edge 窗口等用户登录并**手动关窗**——这是脚本有意为之（保证 cookie 落盘），skill 不要试图代为关窗或干预。
- 不要修改 `get_sapnote.ps1` 的逻辑；它顶部注释有完整说明，需要细节去读它。
- **缓存上限 100 条由 skill 负责清理，脚本不管**：抓到新 note 落盘后，若 `sap-notes/` 里 note 文件数 > 100，按工作流第 2c 步删最旧几条至 ≤ 100。别去改脚本加清缓存逻辑。

## 常见错误（前车之鉴，务必避免）

- **错误：没读 SKILL.md 正文就动手。** 只看 frontmatter description 就开始拼命令，会漏掉缓存机制、脚本路径、禁止项。**正确做法：调用本 skill 后，第一件事就是 Read 本 SKILL.md 全文。**
- **错误：自拼 `msedge --headless --dump-dom` 或用 WebFetch 抓 SAP Note。** SAP session cookie 是 HttpOnly，这些方式都带不上 cookie，只会拿到登录页或 SPA 空壳。**正确做法：一律走 `get_sapnote.ps1`。**
- **错误：去 `~/.claude/skills` 下找脚本。** 本 skill 在项目目录 `.claude/skills/sap-note/` 下，用户主目录的 `.claude/skills` 里没有。**正确做法：用本文件里写明的项目相对路径 `.claude/skills/sap-note/get_sapnote.ps1`。**
- **错误：缓存已有还重新抓。** 浪费网络且可能触发不必要的登录。**正确做法：先查 `sap-notes/<编号补零10位>.json` 缓存。**
