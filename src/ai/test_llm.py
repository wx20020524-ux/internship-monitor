from src.ai.llm import chat_with_llm


if __name__ == "__main__":

    print("=" * 60)
    print("阿里云百炼 LLM 接口测试")
    print("=" * 60)

    try:

        result = chat_with_llm(
            "请只回复：AI岗位推荐模块连接成功"
        )

        print("\n模型返回：")
        print(result)

        print("\n" + "=" * 60)
        print("LLM 调用成功！")
        print("=" * 60)

    except Exception as error:

        print("\nLLM 调用失败！")
        print(error)