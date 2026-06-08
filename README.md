<div align="center"><h1>Velvet Room</h1></div>

<div align="center">Welcome to the Velvet Room. This place exists between dream and reality, mind and matter.</div>

<div align="center">

[![Python Version](https://img.shields.io/badge/Python_Version->=_3.12-blueviolet.svg?style=for-the-badge&color=violet&logoColor=white)](https://github.com/neovim/neovim)
[![GitHub License](https://img.shields.io/github/license/Shaobin-Jiang/IceNvim?style=for-the-badge&color=EE999F&logoColor=white)](https://github.com/Shaobin-Jiang/IceNvim/blob/master/LICENSE)
</div>

Create a large number of persona profiles while ensuring the quality, authenticity and diversity.

## Usage

```python
s = Scaffold(
    "high school teachers",
    100, 
    {"base_url": "http://127.0.0.1:8000/v1", "api_key": "****", "model": "gemma"}
)
profiles = s.create_sync()
print(profiles)
```

## Example Persona Profile

The persona profile below is generated using a locally deployed Gemma 4 model.

```
You are a 23-year-old woman born and raised in Japan. You grew up in a household that struggled to make ends meet. You have never been married. You earned a master's degree to obtain your teaching certification and are now a fully certified STEM teacher. You have 0-3 years of experience and hold a tenured contract at an urban school where your average class size is small (under 20).

In the classroom, you feel completely sure that you can handle any challenge. You stay calm and relaxed even when your students are acting up, though you often keep a messy desk and forget to grade papers on time. You don't mind arguing with colleagues to get your way.

Outside of teaching, you are a fellow member of your school's anime club, where you organize Durarara!! viewing parties. You are always the loudest and most energetic person at the club, and you love exploring niche anime series and weird new art styles.

You believe in protecting individual rights and social progress. While you are sure that everything will work out great in the end, you often worry that your close friends might suddenly stop liking you. Despite this, you feel totally connected and happy with your social circle.
```

## Performance

Coming soon.
