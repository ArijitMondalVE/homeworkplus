from openai import OpenAI
from openai import AuthenticationError, APIConnectionError, RateLimitError

def is_openai_key_valid(api_key: str):
    try:
        client = OpenAI(api_key=api_key)

        # Lightweight request
        client.models.list()

        return True, "API key is valid."

    except AuthenticationError:
        return False, "Invalid API key."

    except RateLimitError:
        return True, "API key is valid, but you've hit the rate limit."

    except APIConnectionError:
        return False, "Could not connect to OpenAI."

    except Exception as e:
        return False, f"Error: {e}"


if __name__ == "__main__":
    key = input("Enter OpenAI API Key: ").strip()

    valid, message = is_openai_key_valid(key)

    print(message)