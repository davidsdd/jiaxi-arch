# 西安交通大学创新港校区室外三维模型

下载或克隆本仓库后，双击根目录的 **index.html** 即可离线查看三维模型，无需启动服务器。支持旋转、缩放、建筑逐栋显示隐藏、环境开关、尺寸查询、3DS 下载与视图导出。浏览器需支持 WebGL 2。

鼠标左键拖动平移，右键拖动旋转，滚轮以指针所在位置缩放。触屏单指平移，双指平移或捏合缩放；开启“旋转”后可单指旋转。加载条显示读取、解码、几何解析和首帧绘制的阶段进度与总体百分比。

模型包含 55 栋建筑及道路、广场、绿地、水景和运动场。Rhino 原生文件有 56 个图层：每栋建筑独立一层，环境共用一层。模型单位为米。

**这是依据公开地图和工程资料制作的近似体块模型。** 部分高度、局部体块分区、道路宽度、景观树位与地形为估算，不能作为实测或施工依据。详细来源、精度说明和 Rhino 导入方法见 [使用说明](output/使用说明.md)。

## 文件

- [index.html](index.html)：自包含离线三维查看器。
- [分层 Rhino 模型](output/XJTU_InnovationHarbour_Layered.3dm)：Rhino 7/8 原生文件。
- [3DS 模型](output/XJTU_InnovationHarbour.3ds)：通用三角网格模型。
- `output/`：尺寸与来源表、图层映射、Rhino 图层恢复脚本、预览及校验结果。
- `scripts/`：建模、预览、查看器源代码和校验脚本。
- `sources/`：建模采用的公开 OSM 数据与派生地理数据。

## 重新生成网页

需要 Node.js、npm 和 Python 3。模型及预览已随仓库提供，仅构建网页无需安装建模依赖。

```sh
npm ci
npm run build
```

生成结果仍为根目录 `index.html`；三维引擎、模型、尺寸信息和静态预览全部内嵌。

校验 3DS 文件：

```sh
npm run check:3ds
```

若需要重新生成 CAD 模型和预览，在 Python 虚拟环境中安装 `scripts/requirements.txt`，再依次运行 `scripts/build_campus.py`、`scripts/render_preview.py` 和 `npm run build`。中文预览字体优先使用 macOS 自带字体。

## 数据来源

建筑名称与布局参考 [学校创新港地图](https://vi.xjtu.edu.cn/cxg/cxgdt.htm)，主要高度采用 [公开工程资料](https://24959527.s21i.faiusr.com/61/ABUIABA9GAAgn5zYpQYowILN7gI.pdf)。平面采用 © OpenStreetMap contributors 数据，OSM 及派生地理数据库按 [ODbL](https://www.openstreetmap.org/copyright) 提供；使用时请保留来源与署名。

原始下载的 PDF、地图图片、临时文件、依赖、缓存和重复压缩包已由 `.gitignore` 排除。
