from typing import Optional

from langchain_core.language_models.chat_models import AzureChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI, ChatOpenAI

from browser_use.agent.predefined_actions import get_predefined_actions
from browser_use.agent.service import Agent


def create_openai_agent(
	api_key: str,
	model_name: str = 'gpt-4-vision-preview',
	temperature: float = 0.7,
	max_tokens: int = 4096,
	initial_actions: Optional[list] = None,
) -> Agent:
	"""
	Create an agent using OpenAI's model
	"""
	llm = ChatOpenAI(api_key=api_key, model_name=model_name, temperature=temperature, max_tokens=max_tokens)

	return Agent(task='Browser automation task', llm=llm, initial_actions=initial_actions or get_predefined_actions())


def create_google_agent(
	api_key: str,
	model_name: str = 'gemini-pro-vision',
	temperature: float = 0.7,
	max_tokens: int = 4096,
	initial_actions: Optional[list] = None,
) -> Agent:
	"""
	Create an agent using Google's Gemini model
	"""
	llm = ChatGoogleGenerativeAI(api_key=api_key, model_name=model_name, temperature=temperature, max_tokens=max_tokens)

	return Agent(task='Browser automation task', llm=llm, initial_actions=initial_actions or get_predefined_actions())


def create_azure_agent(
	api_key: str,
	deployment_name: str,
	model_name: str = 'gpt-4-vision-preview',
	temperature: float = 0.7,
	max_tokens: int = 4096,
	initial_actions: Optional[list] = None,
) -> Agent:
	"""
	Create an agent using Azure OpenAI's model
	"""
	llm = AzureChatOpenAI(
		api_key=api_key, deployment_name=deployment_name, model_name=model_name, temperature=temperature, max_tokens=max_tokens
	)

	return Agent(task='Browser automation task', llm=llm, initial_actions=initial_actions or get_predefined_actions())


def create_anthropic_agent(
	api_key: str,
	model_name: str = 'claude-3-opus-20240229',
	temperature: float = 0.7,
	max_tokens: int = 4096,
	initial_actions: Optional[list] = None,
) -> Agent:
	"""
	Create an agent using Anthropic's Claude model
	"""
	llm = ChatAnthropic(api_key=api_key, model_name=model_name, temperature=temperature, max_tokens=max_tokens)

	return Agent(task='Browser automation task', llm=llm, initial_actions=initial_actions or get_predefined_actions())


# Example usage:
if __name__ == '__main__':
	# Example 1: Using OpenAI
	openai_agent = create_openai_agent(api_key='your-openai-api-key', model_name='gpt-4-vision-preview')

	# Example 2: Using Google Gemini
	google_agent = create_google_agent(api_key='your-google-api-key', model_name='gemini-pro-vision')

	# Example 3: Using Azure OpenAI
	azure_agent = create_azure_agent(api_key='your-azure-api-key', deployment_name='your-deployment-name')

	# Example 4: Using Anthropic Claude
	anthropic_agent = create_anthropic_agent(api_key='your-anthropic-api-key', model_name='claude-3-opus-20240229')
