Pushing the initial commit to a remote

1. Create a new repository on GitHub (or GitLab/Bitbucket) using the web UI. Do NOT initialize with a README or license if you plan to push this repo.

2. Add the remote and push from PowerShell:

```powershell
# replace URL with your repository URL
git remote add origin https://github.com/USERNAME/REPO.git
# or use SSH
# git remote add origin git@github.com:USERNAME/REPO.git

git branch -M main
git push -u origin main
```

Authentication notes:
- For HTTPS: Git will prompt for credentials. Use a personal access token (PAT) for GitHub when prompted for password.
- For SSH: Ensure your SSH key is added to your GitHub account.
