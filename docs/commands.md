## Lab4 -> saving logs in docs/lab4-build-green.logs:

1. Define the save_log Helper Function
First, paste this helper function into your shell (bash or zsh):
usage: save_log <codebuild-build-id> <output-file>
Bash
```
save_log () {   
  read -r G S <<< "$(aws codebuild batch-get-builds --ids "$1" \
      --query 'builds[0].logs.[groupName,streamName]' --output text)"
  aws logs filter-log-events --log-group-name "$G" --log-stream-names "$S" --output json \
    | python3 -c 'import json,sys; sys.stdout.write("".join(e["message"] if e["message"].endswith("\n") else e["message"]+"\n" for e in json.load(sys.stdin)["events"]))' \
    > "$2"
}
```
2. Find Your Final Green Build ID
Find the ID of your most recent SUCCEEDED CodeBuild run:
```
Bash
aws codebuild list-builds-for-project --project-name northstar-ci --query 'ids[0]' --output text
```
You can verify its status is SUCCEEDED with:
```
Bash
B=$(aws codebuild list-builds-for-project --project-name northstar-ci --query 'ids[0]' --output text)
aws codebuild batch-get-builds --ids "$B" --query 'builds[0].[id,buildStatus]' --output text
```
3. Extract the Green Log
Run save_log using that build ID to write the log into docs/lab4-build-green.log:
```
Bash
save_log "$B" docs/lab4-build-green.log
```

Notes: 
northstar-ci:629ff630-8ecb-48aa-b99e-07eeab269cbf