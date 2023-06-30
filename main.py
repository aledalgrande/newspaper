import os
import requests
import openai
import tiktoken
from jinja2 import Environment, FileSystemLoader
import yaml
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from newspaper import Article

class ProgressBarSingleton:
    _instance = None
    progress_bar = None
    total_cost = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgressBarSingleton, cls).__new__(cls)
        return cls._instance


class RelevanceScorer:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = self.api_key
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.MAX_TOKENS = 2048

    def truncate_text(self, text):
        tokens = list(self.tokenizer.tokenize(text))
        if len(tokens) > self.MAX_TOKENS:
            return ''.join(tokens[:self.MAX_TOKENS])
        return text

    def score_relevance(self, text, interests, negatives):
        text = self.truncate_text(text)
        functions = [
            {
                "name": "calculate_relevance",
                "description": "Calculate the relevance of the text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "integer",
                            "description": "The relevance score of the text",
                        },
                    },
                    "required": ["score"],
                },
            }
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable AI. Your task is to evaluate the following text and provide a relevance score between -10 and 10. A score of 10 means the text is highly relevant to the provided interests, a score of -10 means the text is highly relevant to the unwanted topics, and a score of 0 means the text is neutral. Proceed to calculate the relevance score."},
                {"role": "user",
                    "content": f"Interests: {', '.join(interests)}. Unwanted topics: {', '.join(negatives)}. Here is the text: {text}"},
                {"role": "assistant", "content": text}
            ],
            functions=functions
        )
        token_count = response['usage']['total_tokens']
        cost = token_count / 1000 * 0.0015
        if response['choices'][0]['message']['role'] == 'function' and response['choices'][0]['message']['name'] == 'calculate_relevance':
            score = response['choices'][0]['message']['function_call']['args'][0]
            ProgressBarSingleton.total_cost += cost
            ProgressBarSingleton.progress_bar.set_description(
                f"Generating newspaper (cost: ${ProgressBarSingleton.total_cost:.4f})")
            return score

        return -10


class CommentFinder:
    def __init__(self, scorer):
        self.scorer = scorer

    def get_most_relevant_comment(self, story_id, interests, negatives, progress_bar, total_cost):
        story_detail = requests.get(
            f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json').json()
        comments = story_detail.get('kids', [])

        # Limit the number of comments to 50
        comments = comments[:50]

        max_score = -1
        most_relevant_comment = None
        for comment_id in comments:
            comment = requests.get(
                f'https://hacker-news.firebaseio.com/v0/item/{comment_id}.json').json()
            comment_text = comment.get('text', '')
            score = self.scorer.score_relevance(
                comment_text, interests, negatives)
            if score > max_score:
                max_score = score
                most_relevant_comment = comment

        if most_relevant_comment:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable AI."},
                    {"role": "user", "content": "Does this comment provide any unique insights or interesting information?"},
                    {"role": "assistant",
                        "content": most_relevant_comment['text']}
                ]
            )
            if "no" in response['choices'][0]['message']['content'].lower():
                token_count = response['usage']['total_tokens']
                cost = token_count / 1000 * 0.002
                ProgressBarSingleton.total_cost += cost
                ProgressBarSingleton.progress_bar.set_description(
                    f"Generating newspaper (cost: ${ProgressBarSingleton.total_cost:.4f})")
                return most_relevant_comment
        return None


class UserPreferences:
    @staticmethod
    def get_user_preferences():
        with open('preferences.yml', 'r') as file:
            preferences = yaml.safe_load(file)
        return preferences


class NewspaperGenerator:
    def __init__(self, scorer, comment_finder):
        self.scorer = scorer
        self.comment_finder = comment_finder

    def fetch_and_summarize(self, url):
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
        article.nlp()
        summary = article.summary
        return summary

    def generate_newspaper(self, preferences):
        top_stories = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json').json()

        relevant_stories_comments = []
        total_cost = 0

        ProgressBarSingleton.progress_bar = tqdm(
            top_stories[:10], desc="Generating newspaper")

        for story_id in ProgressBarSingleton.progress_bar:
            story = requests.get(
                f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json').json()

            if 'url' in story:
                parsed_uri = urlparse(story['url'])
                result = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
                if result != 'https://news.ycombinator.com/':
                    summary = self.fetch_and_summarize(story['url'])
                else:
                    summary = story['title']
            else:
                summary = story['title']

            score = self.scorer.score_relevance(
                summary, preferences['interests'], preferences['negatives'])

            if score > 0:
                relevant_comment = self.comment_finder.get_most_relevant_comment(
                    story_id, preferences['interests'], preferences['negatives'], progress_bar, total_cost)
                relevant_stories_comments.append(
                    (story, summary, relevant_comment))

        print(f'Total cost: ${ProgressBarSingleton.total_cost:.4f}')

        # Create a 'history' directory if it doesn't exist
        if not os.path.exists('history'):
            os.makedirs('history')

        # Generate a unique filename based on the current date and time
        filename = f'history/newspaper_{datetime.datetime.now().strftime("%Y%m%d_%H%M")}.html'

        # Render the template and save the output to the file
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template('template.html')
        output = template.render(stories=relevant_stories_comments)
        with open(filename, 'w') as f:
            f.write(output)


if __name__ == '__main__':
    api_key = os.getenv('OPENAI_API_KEY')
    scorer = RelevanceScorer(api_key)
    comment_finder = CommentFinder(scorer)
    newspaper_generator = NewspaperGenerator(scorer, comment_finder)
    newspaper_generator.generate_newspaper(UserPreferences.get_user_preferences)
