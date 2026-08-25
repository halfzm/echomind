# 项目概述
一个基于MiniCPM的恋爱分析平台

# 快速启动
```bash
pip install -r requirements.txt
python main.py
```
打开`localhost:8000`即可访问。

# 结构目录
```text
- main.py     项目入口文件、路由入口
- models.py   各种数据结构定义
- utils.py   功能函数
- static/index.html 前端页面
```

# 参考项目
- [MiniCPN-v](https://github.com/OpenBMB/MiniCPM-V)
- [MiniCPM-o-Demo](https://github.com/OpenBMB/MiniCPM-o-Demo)
- [simp-skill](https://github.com/BeamusWayne/simp-skill/tree/main)


## MiniCPM模型测试
> https://minicpmo45.modelbest.cn/turnbased

- 如果上传多个附件，只会处理最后一个

比如依次上传两张图片，问图片中是什么内容，只会分析最后一张图片

比如依次上传一张图片，一个音频，问图片中有什么信息，音频中有什么信息，只会分析音频中的内容且会自己补充不存在的内容


- 图片识别结果不是特别准确

发送人不准，

文字有时也不准，可能会产生不存在的聊天记录


- 文字回复也不太精准
比如说指定了回复格式，有时候依然会乱


提取图片聊天记录的提示词--暂时用不到

请从上至下逐行解析这张聊天截图，输出严格为JSON数组，不要任何多余文字、解释、注释。
每个数组对象字段固定：
1. timestamp：截图中消息附带的时间文本，识别不到则为空字符串""
2. sender：左侧气泡=other；右侧气泡=me
3. content：消息完整文字内容，原样保留，不要删减修改
4. msg_type：固定填"文字"

规则：
1. 严格遵循截图从上到下的聊天时序；
2. 图片、表情包、语音消息直接忽略，不生成json条目；
3. 不要合并多条消息，一条气泡对应一条json对象；
4. 只返回JSON，禁止输出其他内容。



