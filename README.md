# RookieAI_yolov8

## 版本要求

| Version | Python |
|---------|--------|
| `2.4.3或更早`   | 3.7+   |
| `2.4.4.2+`   | 3.10+   |

## 使用方法：

前言：为维护环境不提供直接打包成型的软件，开源代码鼓励自学。

使用前务必查看[参数说明文档](Parameter_explanation.md)

> [!Warning]
>
> 使用前请先阅读[参数解释文档](Parameter_explanation.md)
>
> 目前正在编写适用于新手的一键式启动器
>
> 如果你只是本地运行该项目，请**不要使用**pyinstaller打包 
> 
> 打包方法尚未完善，遇到问题也**不要提交**Issues，请自行解决

### 针对开发者：

1. ### 使用以下代码获取本代码需要的库与Pytorch库：

   **✨ 超高速无痛下载 ✨**
   
   ```shell
   pip install -r requirements.txt -i https://pypi.doubanio.com/simple/
   pip install torch torchvision torchaudio -f https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html --no-index
   ```

2. ### 你还需要一个自己的模型（目前支持.pt/.engine/.onnx模型），如果没有可暂时使用ultralytics官方模型。

3. **当未找到模型时会自动下载YOLOv8n模型，你也可以⬇️**

   访问[YOLOv8GitHub界面](https://docs.ultralytics.com/)获取更多官方yolov8模型以快速开始
   
   访问[ultralytics官网](https://docs.ultralytics.com/)查看官方网站帮助文档

4. ### 使用你的模型

   打开软件>选择模型文件>保存设置>关闭软件，重启软件。
   
   即可加载上选择的模型文件
   
   或者：
   
   修改默认文件地址：
   
   ```
   #默认的模型文件地址
   default_model_file="yolov8n.pt"
   ```

### 针对想直接使用者：

> 此处教程未更新，**仅供参考**

> 如果您是开发者，无需阅读此步骤，使用终端运行即可

1. ### 使用以下代码获取本代码需要的库与Pytorch库：
   ```shell
   pip install -r requirements.txt
   pip install torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu121
   ```

2. ### 下载pyinstaller库(打包用)

`pip install pyinstaller`

3. ### 使用pyinstaller打包代码

   `pyinstaller xxxxx.py`
   
   将xxxxx替换为代码实际名称。
   
   更多打包参数介绍：[Pythonpyinstaller打包exe最完整教程](https://blog.csdn.net/qq_48979387/article/details/132359366)

   ❗必定会遇到的问题：
   
   Q：运行提示`FileNotFoundError:`，问题：缺少库
   
   A：把编译器虚拟环境里的库全部复制粘贴到打包出的文件夹<_internal>里就可以了。
   
   参考：[打包后库不全解决办法](https://github.com/Passer1072/RookieAI_yolov8/issues/1#issuecomment-2041157885)

4. ### 关于模型文件

   建议自行训练
   
   学习资料：
   
   [Bilibili](https://search.bilibili.com/all?keyword=%E5%A6%82%E4%BD%95%E8%AE%AD%E7%BB%83%E6%A8%A1%E5%9E%8B&from_source=webtop_search&spm_id_from=333.1007&search_source=5)
   
   [YouTube](https://www.youtube.com/results?search_query=how+to+train+yolov8+model)
   
   ❗在软件中选择完模型文件后需保存重启后才会生效，因为需要重新加载模型。

5. ### 文件整理

   将
   ```txt
   _internal(包含软件环境/库)
   body_photo.png（软件需要的图片1）
   logo-bird.png（软件需要的图片2）
   程序.exe（主程序）
   settings.json(参数保存)
   模型文件.pt（模型文件）
   ```
   
   放在同一目录下，直接运行exe文件即可。

oldGUI版与newGUI版对比图：

![logo](images/oldGUI&newGUI.png)
Ps:二者在最终使用效果上无任何区别，仅视觉差异

🎉全新V2.0版本，全新布局，更好优化，更多设置

![V2.4.3](images/V2.4.3.png)

### 推荐使用Atlas游戏系统配合boosterX性能优化软件获得更好体验

[AtlasOS](https://atlasos.net/)对 Windows 进行修改，专为游戏玩家设计。具有更高的游戏帧率和更低的延迟。同时在此系统上使用RookieAI可更高效的利用GPU资源得到更高的推理帧率。

[boosterX](https://boosterx.org/en/)是一款系统优化软件，优化Windows，降低延迟、提高 FPS。在AtlasOS系统上使用可进一步进行优化。

配置单：截图模式:mss  截图高/宽:320  显卡:RTX4080M  模型:YOLOv8s_TheFinals_teammate_enemy_04.engine

原版windows空载运行RookieAI2.4.3 对比 AtlasOS 空载运行RookieAI2.4.3：



### ✅✅✅注意✅✅✅

此项目最初目的为Apex的Aimbot，未考虑其他游戏，可能会出现因反作弊禁止WIN32移动方式而无法使用的情况！

已知游戏：**VALORANT**

面对日益增多的配置文件参数，我新建了参数解释文档，里面介绍了配置文件内所有参数的信息，前往[参数解释文档](Parameter_explanation.md)查看。

**🎉🎉🎉非常感谢由RicardoJoaquim提供的英文特别版本🎉🎉🎉**

### 最后想说的：

> [!Important]
> 由于底层代码问题，推理帧数始终优化不上去，目前的代码也找不到更多可优化的空间（已经有些屎山代码了），我正在考虑完全重写整个程序，包括但不限于：
> 使用PyQt6重写UI界面，使用多进程优化程序，优化整体代码逻辑架构等。敬请期待。

**目前学业繁忙，随缘更新，敬请谅解 :(**


### 更新日志：

[已迁移](CHANGELOG.md)

___

Current latest version: ###
