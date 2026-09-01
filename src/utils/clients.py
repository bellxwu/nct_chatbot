import os
USE_GATEWAY = (os.getenv('USE_GATEWAY', 'FALSE').upper() == 'TRUE')

def get_client(provider: str, use_gateway: bool = USE_GATEWAY): 
    if use_gateway:
        client = provider(base_url='insert_url',
                    api_key='any value',
                    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')})
    else:
        if provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic()
        elif provider == 'openai':
            import openai
            client = openai.OpenAI()
        else:
            raise ValueError("Specify model provider: 'anthropic', 'openai' ")
    return client