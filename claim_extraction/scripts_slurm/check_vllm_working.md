squeue -u $USER -o "%.18i %.9P %.8T %.10M %.20R" # Check job
srun --jobid 6194405 --pty bash -l #Get inside job terminal
ss -ltnp | grep 8000 || netstat -ltnp | grep 8000 #Check if server is listening

#----------------End to end test---------------------------------
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
    "messages": [{"role":"user","content":"Reply with exactly: OK"}],
    "temperature": 0,
    "max_tokens": 10
  }'

