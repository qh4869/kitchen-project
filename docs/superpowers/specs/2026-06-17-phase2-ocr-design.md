# Phase 2 设计：OCR 视觉化记账链路

**状态**：已通过头脑风暴评审，待实现
**日期**：2026-06-17
**关联**：[Phase 1 实现方案](../../../.claude/plans/prd-txt-1-2-1-2-web-cheerful-shannon.md) §4.1 视觉化记账

## 1. 背景与目标

PRD §4.1.1 要求"拍照识别小票 / 货架价签 → OCR 提取商品名 / 单价 / 数量 → 人工微调 → 落库"。Phase 1 已建好供应商、采购单、采购明细的 CRUD 骨架，本期把 OCR 链路接上。

**本期范围**：
- 新增 `/api/v1/uploads`、`/api/v1/ocr/extract`、`/api/v1/purchases/from-ocr` 三个端点
- 实现可插拔 OCR 适配器，默认走火山方舟 OpenAI 兼容接口
- UploadPage 前端：单图上传 → OCR → 表格微调 → 落库
- 单元测试用 mock 适配器，集成测试可选

**显式不做**：
- 多图合并（用户决定本期简化为单图；后续若需要可加，DB schema 已经预留扩展空间）
- 多 LLM 并行投票 / 置信度对比
- 批量小票处理
- 自动类目推断（依赖 LLM 输出，不做后处理）

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 默认模型 | `Doubao-Seed-2.0-mini`（写进 `LLM_MODEL`，可换） | 用户指定；若该模型不支持视觉输入则换 `doubao-1.5-vision-pro`，代码不动 |
| LLM 接口 | OpenAI 兼容（火山方舟 `https://ark.cn-beijing.volces.com/api/v3`） | 一份代码兼容火山 / OpenAI / Qwen / Deepseek 等 |
| HTTP 客户端 | `httpx.AsyncClient` 直连，不引入 openai SDK | OCR 是单次 chat completions 调用，无 stream；少一个依赖 |
| 图片数量 | 单图 | 用户简化决策；多图代码复杂度直接减半 |
| 失败处理 | OCR 返空 / 缺价格 → 不落库 → 前端提示「未识别到信息」+ 提供「重拍」/「手工录入」 | 用户决策 |
| 图片约束 | 单张 ≤ 10 MB；JPEG / PNG / WebP / HEIC；长边 > 2000px 时 Pillow 等比缩放 | 手机照片常见尺寸，控制 LLM token 消耗 |
| OCR 超时 | 单次 10s | 超时即向 frontend 上报 `504 OCR_TIMEOUT`，前端区分提示 |
| 测试策略 | mock 适配器跑单测；真 API 集成测试 `pytest -m integration` 默认跳过 | 单测要快、确定、零成本 |

## 3. 架构

### 3.1 模块新增

```
apps/api/app/
├── services/                      # 新增整个目录
│   ├── __init__.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── adapter.py             # OcrAdapter 协议 + create_ocr_adapter 工厂
│   │   ├── openai_compat.py       # 唯一真实适配器：覆盖火山/OpenAI/Qwen/Deepseek
│   │   ├── mock.py                # 测试用假适配器，返固定 JSON
│   │   └── prompt.py              # 共享 prompt 模板，强约束 JSON 输出
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── adapter.py             # FileStorage 协议 + create_storage 工厂
│   │   ├── local.py               # 本地磁盘实现，写入 UPLOAD_DIR
│   │   └── image.py               # Pillow 预处理（旋转矫正 + 长边缩放）
│   └── analysis/                  # 预留 Phase 3，本期空目录
│       └── __init__.py
├── routers/
│   ├── uploads.py                 # 新增：multipart 上传 → Pillow → storage
│   └── ocr.py                     # 新增：POST /ocr/extract 调适配器
├── schemas/
│   └── ocr.py                     # 新增：OcrResult / OcrItem / OcrExtractRequest
└── routers/purchases.py           # 扩展：新增 POST /purchases/from-ocr
```

### 3.2 数据流（单图版）

```
浏览器                      后端                         火山方舟
  │
  │  POST /api/v1/uploads (multipart)
  │────────────────────────────▶│
  │                              │ Pillow 预处理
  │                              │ storage.save() → ./uploads/{uuid}.jpg
  │  ◀──── {image_key: "..."} ───│
  │
  │  POST /api/v1/ocr/extract {image_key}
  │────────────────────────────▶│
  │                              │ storage.read(image_key) → bytes
  │                              │ base64 → OpenAI 兼容 chat completions
  │                              │──────────────────────────────▶│
  │                              │  ◀──── content (JSON 字符串) ──│
  │                              │ 解析 JSON → OcrResult
  │  ◀──── OcrResult ────────────│
  │
  │  [若 items 为空或全缺价格]
  │  显示红字「未识别到信息」+ 重拍/手工按钮
  │  ⛔ 不调用 from-ocr
  │
  │  [若至少一条有效]
  │  ItemEditor 表格编辑
  │
  │  POST /api/v1/purchases/from-ocr {image_key, supplier_id, items, ocr_raw, ...}
  │────────────────────────────▶│
  │                              │ 复用 PurchaseCreate 校验
  │                              │ 落 purchases + purchase_items
  │  ◀──── PurchaseOut ──────────│
```

## 4. API 契约

### 4.1 POST `/api/v1/uploads`

multipart/form-data，字段 `file`。返回：

```json
{
  "image_key": "2026/06/17/{uuid}.jpg",
  "size": 234567,
  "content_type": "image/jpeg"
}
```

- 接受 MIME：`image/jpeg` / `image/png` / `image/webp` / `image/heic` / `image/heif`
- 服务端用 Pillow 打开做格式校验 + EXIF 旋转矫正 + 长边 > 2000px 时等比缩放
- 落盘格式统一转 JPEG（避免 HEIC 浏览器兼容问题）
- `image_key` 用日期分层（`YYYY/MM/DD/{uuid}.jpg`）避免单目录文件过多

错误：
- `400 UPLOAD_TOO_LARGE`：单张 > 10MB
- `400 UNSUPPORTED_IMAGE_TYPE`
- `400 INVALID_IMAGE`（Pillow 无法解析）

### 4.2 POST `/api/v1/ocr/extract`

请求：

```json
{ "image_key": "2026/06/17/{uuid}.jpg" }
```

响应 `OcrResult`：

```json
{
  "image_key": "2026/06/17/{uuid}.jpg",
  "supplier_name": null,
  "purchase_time": null,
  "total_amount": null,
  "items": [
    {
      "name": "番茄",
      "quantity": 1.5,
      "unit": "kg",
      "unit_price": 6.50,
      "category": "蔬菜",
      "brand": null
    }
  ],
  "raw_llm_output": { "...模型解析后的 JSON 对象..." },
  "provider": "volcengine"
}
```

- 任何字段失败时取 `null`；`items` 可能为空数组（这就是「OCR 失败」的语义）
- `raw_llm_output` 是 **已解析的 JSON 对象**（不是字符串），方便前端透传回 `/purchases/from-ocr` 直接落库到 `purchases.ocr_raw` JSONB 列
- 若模型输出无法解析为 JSON，路由返回 502，不构造 OcrResult

错误：
- `404 IMAGE_NOT_FOUND`（image_key 不存在）
- `504 OCR_TIMEOUT`（LLM 调用超过 10s 未响应；前端文案「OCR 超时，请重试或换一张图」）
- `502 OCR_UPSTREAM_ERROR`（LLM 返回非 2xx / 网络错误）
- `502 OCR_PARSE_ERROR`（模型输出无法解析为 JSON）

### 4.3 POST `/api/v1/purchases/from-ocr`

请求（在 `PurchaseCreate` 基础上扩展）：

```json
{
  "image_key": "2026/06/17/{uuid}.jpg",
  "supplier_id": null,
  "purchase_time": "2026-06-17T10:30:00Z",
  "total_amount": "19.50",
  "notes": null,
  "ocr_raw": { "...OcrResult.raw_llm_output 透传..." },
  "items": [
    {"name": "番茄", "quantity": "1.5", "unit": "kg", "unit_price": "6.50", "category": "蔬菜"}
  ]
}
```

- 服务端校验 `items` 非空且每条满足 `name + unit_price`（Pydantic 已强制）
- `ocr_provider` 字段从请求中省略；服务端读 `settings.ocr_provider` 写入
- `manual_adjustment` 默认 `false`，前端检测到用户改过任何字段时传 `true`
- 落库后返回完整 `PurchaseOut`

错误：
- `400 EMPTY_ITEMS`：items 为空
- `404 IMAGE_NOT_FOUND`：image_key 不存在（不强制要求 image_key 必须先 upload，但若是有效 key 则写入 `receipt_image_path`）

## 5. OCR 适配器

### 5.1 协议（`apps/api/app/services/ocr/adapter.py`）

```python
from typing import Protocol
from app.schemas.ocr import OcrResult

class OcrAdapter(Protocol):
    """所有 OCR 实现的统一接口。"""
    provider: str  # 'volcengine' | 'openai' | 'mock' | ...

    async def extract(self, image_bytes: bytes, content_type: str) -> OcrResult: ...

def create_ocr_adapter() -> OcrAdapter:
    """根据 settings.ocr_provider 返回实例。"""
    name = settings.ocr_provider
    if name == "mock":
        from .mock import MockOcrAdapter
        return MockOcrAdapter()
    # 所有 OpenAI 兼容供应商共用一个类
    from .openai_compat import OpenAICompatAdapter
    return OpenAICompatAdapter(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        provider_name=name,
    )
```

### 5.2 OpenAI 兼容实现（`openai_compat.py`）

```python
class OpenAICompatAdapter:
    provider = "openai_compat"  # 创建时被 provider_name 覆盖

    def __init__(self, base_url, api_key, model, provider_name, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider_name
        self.timeout = timeout

    async def extract(self, image_bytes, content_type) -> OcrResult:
        data_url = f"data:{content_type};base64,{base64.b64encode(image_bytes).decode()}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": USER_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if settings.llm_force_json:
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        return parse_llm_json(content, provider=self.provider)
```

`parse_llm_json` 容错：
- 先尝试 `json.loads(content)`
- 失败则正则提取 `{...}` / `[...]` 块再解析
- 仍失败抛 `OcrParseError`，路由层映射为 502

### 5.2.1 异常映射（`apps/api/app/services/ocr/exceptions.py`）

```python
class OcrError(Exception):
    """所有 OCR 适配器错误的基类。"""

class OcrTimeoutError(OcrError):
    """LLM 调用超时。路由映射 504。"""

class OcrUpstreamError(OcrError):
    """LLM 返回非 2xx 或网络错误。路由映射 502。"""

class OcrParseError(OcrError):
    """LLM 输出无法解析为 JSON。路由映射 502。"""
```

`OpenAICompatAdapter.extract` 内部把 httpx 异常翻译成上面三类：

```python
try:
    r = await client.post(...)
    r.raise_for_status()
except httpx.TimeoutException as e:
    raise OcrTimeoutError(f"upstream timeout after {self.timeout}s") from e
except httpx.HTTPStatusError as e:
    raise OcrUpstreamError(f"upstream {e.response.status_code}") from e
except httpx.HTTPError as e:
    raise OcrUpstreamError(f"network: {e!s}") from e

try:
    return parse_llm_json(content, provider=self.provider)
except ValueError as e:
    raise OcrParseError("LLM output not valid JSON") from e
```

`routers/ocr.py` 顶层 except：

```python
@router.post("/extract", response_model=OcrResult)
async def extract(req: OcrExtractRequest, storage: FileStorage = Depends(...)):
    try:
        ...
    except OcrTimeoutError:
        raise HTTPException(504, detail="OCR_TIMEOUT")
    except OcrUpstreamError as e:
        raise HTTPException(502, detail=f"OCR_UPSTREAM_ERROR: {e}")
    except OcrParseError:
        raise HTTPException(502, detail="OCR_PARSE_ERROR")
```

### 5.3 Prompt（`prompt.py`）

System prompt（中文，约 200 字）：

```
你是采购小票 / 货架价签识别助手。你的任务是从用户提供的图片中提取商品信息，并严格输出 JSON。

输出 schema（必须严格匹配，不能添加任何额外字段）：
{
  "supplier_name": string | null,        // 店铺名（看不清就 null）
  "purchase_time": string | null,        // ISO 8601，看不清就 null
  "total_amount": number | null,         // 总金额
  "items": [
    {
      "name": string,                    // 商品名，必填
      "quantity": number | null,         // 数量
      "unit": string | null,             // 单位：kg / 个 / 盒 / 瓶 ...
      "unit_price": number | null,       // 单价（人民币）
      "category": string | null,         // 类目：蔬菜 / 肉类 / 蛋 / 调料 ...
      "brand": string | null             // 品牌
    }
  ]
}

硬性规则：
1. 只输出上面的 JSON 对象，不要 markdown 围栏、不要解释、不要前缀后缀
2. items 数组：能看清几条就写几条；一条都看不清就返空数组 []
3. 看不清的字段写 null，禁止编造或猜测
4. 数字字段必须是 JSON number（不要字符串）
5. 若图片不是小票 / 价签（比如风景照），返 {"items": [], "supplier_name": null, ...}
```

### 5.4 Mock 适配器（`mock.py`）

`MockOcrAdapter` 返回硬编码的 `OcrResult`，用于：
- 单元测试（deterministic、零成本）
- 本地无 API key 时手动测试前端流程（设 `OCR_PROVIDER=mock`）

支持从环境变量 `OCR_MOCK_FIXTURE` 读 fixture 路径，加载不同 JSON。

## 6. 存储抽象（`apps/api/app/services/storage/`）

### 6.1 协议

```python
class FileStorage(Protocol):
    async def save(self, data: bytes, key: str) -> str: ...
    async def read(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    def get_url(self, key: str) -> str: ...   # 给前端用的访问 URL
```

### 6.2 本地实现 `LocalFileStorage`

- 根目录：`settings.upload_dir`（默认 `./uploads`）
- `save`：拼绝对路径，创建父目录，写文件
- `read`：读 bytes
- `get_url`：返回 `/static/{key}`（main.py 已经 mount 了 StaticFiles）

### 6.3 预留 S3 实现

`create_storage` 工厂支持 `STORAGE_DRIVER=s3`，但本期不实现 S3 类，遇到时抛 `NotImplementedError`。Feature 2 边界之外。

### 6.4 Pillow 预处理（`image.py`）

```python
def preprocess_image(raw: bytes) -> tuple[bytes, str]:
    """返回 (processed_bytes, content_type)。"""
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)              # EXIF 旋转矫正
    if max(img.size) > 2000:
        ratio = 2000 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"
```

## 7. 前端 UploadPage（简化版）

布局：单页两段式，上图下表。

```
┌─────────────────────────────────────────────────────┐
│  📷 拍照记账                                          │
├─────────────────────────────────────────────────────┤
│  [拖拽 / 点击上传 / 拍照]                              │
│  ┌──────────────────┐                                │
│  │  缩略图预览        │   状态：✓ 上传完成               │
│  └──────────────────┘       [识别中...] 或 [重新上传] │
├─────────────────────────────────────────────────────┤
│  供应商：[下拉选]    时间：[datetime]    总额：[输入]  │
│  ┌─────────────────────────────────────────────┐    │
│  │ 名称    数量  单位  单价   类目   品牌   ✕    │    │
│  │ 番茄    1.5   kg    6.50   蔬菜   —      ✕   │    │
│  │ 鸡蛋    10    个    1.20   —      —      ✕   │    │
│  │ [+ 添加一行]                                  │    │
│  └─────────────────────────────────────────────┘    │
│  [保存]                                               │
└─────────────────────────────────────────────────────┘
```

状态机：
- `idle`：未上传
- `uploading`：上传中
- `uploaded`：上传完成，等用户点「识别」/自动开始识别
- `recognizing`：调 `/ocr/extract`
- `recognized`：拿到 OcrResult，渲染表格
- `failed`：OCR 失败或 items 空 → 红字提示 + 「重拍」/「手工录入」按钮
- `saving` / `saved`

失败分支（按错误码细分提示）：
- `504 OCR_TIMEOUT`：橙字「OCR 超时（10s），请重试或换一张清晰的图」 + 按钮「重试」/「换图」
- `200 但 items 空`：红字「未识别到任何商品信息，请重拍或改手工录入」 + 按钮「重新上传」/「手工录入」
- `502 OCR_UPSTREAM_ERROR` / `502 OCR_PARSE_ERROR`：红字「OCR 服务异常，请稍后再试」 + 按钮「重试」

所有失败状态都保留已上传图片缩略图，让用户决定是否复用。

字段编辑：所有字段实时双向绑定；任何字段被改动即把 `manual_adjustment` 标记为 `true`。

## 8. 数据库

**无 schema 变更**。Phase 1 已经建好的 `purchases.receipt_image_path TEXT` 直接复用，存 `image_key`。`purchases.ocr_raw` JSONB 存原始 LLM 输出。`purchases.ocr_provider` 存 provider 名称。

未来扩展多图时，再写 Alembic 迁移把单列改成数组或拆出独立表。

## 9. 配置变更（`.env`）

旧（Phase 1 留的）：

```
OCR_PROVIDER=glm
GLM_API_KEY=
GLM_MODEL=glm-4v
```

新：

```
# LLM (OpenAI-compatible; default: 火山方舟)
OCR_PROVIDER=volcengine                  # volcengine | openai | mock
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_API_KEY=
LLM_MODEL=Doubao-Seed-2.0-mini
LLM_FORCE_JSON=true                      # true: 用 response_format=json_object；false: 纯 prompt 约束

# Mock (供本地无 key 时用)
OCR_MOCK_FIXTURE=                         # 可选，fixture JSON 路径
```

`apps/api/app/config.py` 中删除 `glm_api_key` / `glm_model`，新增 `llm_base_url` / `llm_api_key` / `llm_model`。`ocr_provider` 字段保留但可选值改变。

## 10. 测试

### 10.1 单元测试（默认跑）

`tests/test_ocr.py`：
- `MockOcrAdapter.extract()` 返回固定结构
- `parse_llm_json` 各种容错（纯 JSON / 带 markdown 围栏 / 多余文字）
- `OpenAICompatAdapter` 用 `respx` mock httpx，验证请求 body 格式
- `OpenAICompatAdapter` 模拟 httpx 超时 → 抛 `OcrTimeoutError`
- `OpenAICompatAdapter` 模拟 500 响应 → 抛 `OcrUpstreamError`
- 路由层：`OcrTimeoutError` → 504；`OcrParseError` → 502

`tests/test_uploads.py`：
- 上传 PNG → 返回 image_key
- 上传 HEIC → 转 JPEG
- 上传 > 10MB → 400
- 上传非图片 → 400

`tests/test_purchases_from_ocr.py`：
- items 空 → 400
- 正常落库 → `ocr_raw` / `ocr_provider` 正确写入

### 10.2 集成测试（默认跳过）

`tests/integration/test_ocr_real.py`：
- 标记 `@pytest.mark.integration`
- 读 `LLM_API_KEY`，没有则 `pytest.skip()`
- 用 fixture 图 `tests/fixtures/receipt_sample.jpg`（用户在跑集成测试前自己放一张真实小票进去）
- 断言识别出至少 1 个 item 且 `unit_price` 不为 null

`pytest -m integration` 显式开启。`tests/fixtures/` 加入 `.gitignore`（避免提交真实小票）。

### 10.3 手测路径

`.env` 设 `OCR_PROVIDER=mock` → `pnpm dev` → 浏览器走完整上传 → 假数据落库流程，零 API 成本。

## 11. 实施顺序（建议三个提交）

1. **OCR 服务核心**：`schemas/ocr.py` + `services/ocr/{adapter,openai_compat,mock,prompt}.py` + 单测
2. **上传 + OCR 路由**：`services/storage/{adapter,local,image}.py` + `routers/uploads.py` + `routers/ocr.py` + `purchases/from-ocr` + 单测
3. **前端 UploadPage**：替换占位页 + 手测 mock 链路 + 用真 API 跑一次小票识别

## 12. 验收标准

- `pnpm test:api` 全绿（含新增 ~15 个测试）
- `OCR_PROVIDER=mock` 走完上传→识别→编辑→保存，记录出现在采购列表
- `OCR_PROVIDER=volcengine` + 有效 key，上传一张真实超市小票，识别出 ≥1 个 item 且 name/unit_price 正确率 ≥ 80%
- OCR 超时（mock 适配器人为 sleep 11s，或真 API 故意配错 base_url 触发网络超时）→ 前端显示「OCR 超时（10s），请重试或换一张清晰的图」，**不落库**
- OCR 返空 items → 前端显示「未识别到任何商品信息」，**不落库**

## 13. 风险与备选

| 风险 | 缓解 |
|---|---|
| `Doubao-Seed-2.0-mini` 不支持视觉输入 | 改 `.env` 的 `LLM_MODEL=doubao-1.5-vision-pro`，代码不动 |
| 火山方舟不支持 `response_format: {type: json_object}` | OpenAICompatAdapter 加 env 开关 `LLM_FORCE_JSON=true`，关闭后改用纯 prompt 约束 + `parse_llm_json` 容错 |
| Pillow 原生不支持 HEIC | 新增依赖 `pillow-heif`，在 `services/storage/image.py` 顶部 `register_heif_opener()` |
| 大文件上传导致 OOM | FastAPI multipart 默认无限制；用 `Request.body()` 长度判断 + 流式接收，超 10MB 直接 400 |
| LLM 返回非 JSON | `parse_llm_json` 多重容错 + 失败抛 502 |
| 中文小票识别准确率不达标 | prompt 中加 few-shot 示例（后续迭代） |
| 图片过大上传慢 | Pillow 长边 2000px 缩 + JPEG quality 85 |

## 14. 依赖变更（`apps/api/pyproject.toml`）

新增：
- `pillow-heif>=0.18`（HEIC/HEIF 解码，iPhone 默认格式）
- `respx>=0.22`（dev group，mock httpx 测试用）

不变：`httpx` / `Pillow` 已在 Phase 1 装好。
