# tinyci
tinyci (as in Tiny CI) is an experimental CI tool I created for personal usage. It basically pulls files from a repository and copies them to a specific location. Process can be triggered with a webhook. Specific files and folders can be ignored with patterns.

## Requirements
Other than python packages in `requirements.txt` file, `rsync` and `git` are also required.

## Usage

### Crete New Project
Create a folder under `projects` containing a `config.yaml` file.

Example config.yaml

```yaml
# git repo to pull. branch default is master.
git:
   url: git@github.com:ulasozguler/tinyci.git
   branch: master

# where the files will be copied (can be a remote address)
target: /var/web/tinyci

# ignore files/folders with rsync's --exclude param syntax
ignore:
   - uploads/*
```

### User Management
Users are saved to a file called `users` in the root folder. 

Add a line like `username,pass_md5_hash` for user management.

Super sophisticated stuff.

### Webhooks
Something like `http://user:pass@127.0.0.1:8080/projects/<projectname>/deploy` can be used with a webhook.

## Improvements
- Slack/email notifications
- Custom script support for pre/post deployment

## Notes
- If you have never connected to your repo host from your server before, you may need to manually make the host authenticity verification for the first time.
- Nothing is tested, everything can go to hell pretty fast.