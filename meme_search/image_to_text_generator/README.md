# image to text generator

This directory contains the image to text generator code, server, and queue for meme search pro.

To run the app locally using Docker you can use the repo's `compose` files.

Note run the app natively the route to the internal job queue must be adjusted, as the default is set to a location in the docker container. Run the app in `test` mode to most easily make this adjustment.

To do this first use pip or [uv](https://github.com/astral-sh/uv) to create a venv. For example, with uv you first create a virtual environment and install the requirements:

```bash
uv venv --python 3.12.0
```

Enter the venv, and install the requirements:

```bash
uv pip install -r requirements.txt
```

Then you can run the app in test mode: as

```bash
python app/app.py 'testing'
```

This adjusts the location of the job queue database to `/tests/db/job_queue.db`.

# Model memory

The service loads the selected model once and reuses it for every job. Switching the model in Settings releases the old one before the new one is loaded, so only one model is in memory at a time.

When no job has run for `MODEL_IDLE_TIMEOUT` seconds (default `300`), the model is released to free RAM or GPU memory; the next job loads it again. Set `MODEL_IDLE_TIMEOUT=0` to keep it loaded until the service stops. With Docker Compose, set the variable in `.env`.

# Running tests

You can run the current suite of tests for the image to text generator by running

```bash
pytest tests/test_app.py
```