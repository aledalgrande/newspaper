# HackerNewspaper

HackerNewspaper is a Python package that curates and summarizes top stories from Hacker News. It's designed for tech enthusiasts, developers, and anyone who wants to stay updated with the latest technology and science news while avoiding certain topics.

* mostly GPT generated
Sure, here's an example of a `README.md` file for a project named "HackerNewspaper":

## Installation

Before you start, ensure you have installed [Python](https://www.python.org/downloads/) and [Poetry](https://python-poetry.org/docs/#installation) on your machine.

To install the package, follow these steps:

1. Clone the repository:

```bash
git clone https://github.com/aledalgrande/HackerNewspaper.git
```

2. Navigate to the repository folder:

```bash
cd HackerNewspaper
```

3. Install the package:

```bash
poetry install
```

## Usage

To use HackerNewspaper, first, update your preferences in the `preferences.yaml` file. Define your interests and any topics you want to avoid.

Then, run the main script:

```bash
python main.py
```

This will fetch the top 10 stories from Hacker News, score them based on your preferences, and generate a newspaper with the most relevant stories and comments.

## Contributing

Contributions are always welcome! Please read the [contribution guidelines](CONTRIBUTING.md) first.

## License

This project is licensed under the terms of the [MIT license](LICENSE.md).
