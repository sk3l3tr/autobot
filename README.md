<div align="center">
  <a href="https://github.com/N0M4D-D3V/autobot">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="resources/icon_dark.png">
      <source media="(prefers-color-scheme: light)" srcset="resources/icon.png">
      <img src="resources/icon.png" width="150">
  </picture>
  </a>

<h3 align="center" style="font-size:3rem">AUT0B0T DESKTOP</h3>
  <p align="center">
The Autobot application is a desktop/web hybrid solution for automated HMI interactions.
  </p>
</div>

## D3V ENVIRONMENT

### Prerequired

- Python +3.10
- NodeJS +18 (nvm recomended)

### Instalation

1. Create new python environment for python dependencies management. At `./` execute

   ```zsh
    python -m venv /path/to/new/virtual/environment
    source /path/to/new/virtual/environment/bin/activate

    pip install -r requirements.txt
   ```

2. Build your frontend. Navigate to `./frontend` and execute
   ```zsh
    npm install && npm run build
    npm run deploy:local
   ```
3. Build the binaries. Navigate to `./webhook_agent` and execute

   ```zsh
   # you may need to create the files/bin folder
   npm install && npm run deploy:local
   ```

4. Run for development. Return to `./` and execute this to run the app

   ```zsh
    python main.py
   ```

### CLI

You can also install the project as a Python package and run robotizations directly from the terminal:

```zsh
pipx install .
autobot list
autobot run my_robot
autobot write my_robot
```

5. (Optional) Windows only. Create the icon for the app.

   ```zsh
    python create_icon.py
   ```

6. Build for distribution. Go to project root directory. Then exec:

   ```zsh
    python packager.py
   ```

> This will package all the product. Be sure you compiled every module before package. Be sure the compilation mode of others modules is correct (development or production). Take care about webhook keys, private data or any private configuration before distribution.

## Examples

### cURL

You can send a cURL request to webhook to emulate a request and test the flow. This is just an example, you can send and test any kind of available action.

```
curl -X 'POST' 'https://webhook.site/Billions' -H 'content-length: 52' -H 'content-type: application/json' -H 'authorization: Bearer 8056902b-834c-4d6c-acfc-d6c43835d966' -H 'accept: */*' -H 'user-agent: curl/8.7.1' -H 'host: webhook.site' -d $'{"action": "run_robot", "kwargs": {"name": "my_robot"}}'
```

### nc

You can send orders to local socket directly using any local soket client. This is just an example, but you can use any other terminal client.

```
printf '{"action":"run_robot","kwargs":{"name":"my_robot"}}' | nc 127.0.0.1 65432
```
