# Troubleshooting Guide

## What Happened in Your Run

### ✅ What Worked

1. **Environment Setup**: ✅
   - VM started successfully
   - Connected to OSWorld server
   - Got screenshots and accessibility trees
   - Agent initialized correctly

2. **Agent Initialization**: ✅
   - GPT-4o-mini agent loaded
   - Connected to OpenAI API

### ❌ What Went Wrong

#### Issue 1: Rate Limiting (HTTP 429)

**What you saw:**
```
HTTP/1.1 429 Too Many Requests
Rate limit hit, waiting 2s before retry...
Rate limit hit, waiting 4s before retry...
Rate limit hit, waiting 8s before retry...
Failed to call OpenAI API after all retries
```

**What it means:**
- Your OpenAI API key hit rate limits
- The API returned "Too Many Requests" error
- The agent tried multiple times but couldn't get through

**Why this happens:**
1. **Free Tier Limits**: OpenAI free tier has strict limits (e.g., 3 requests per minute)
2. **Account Setup**: You might need to add billing information
3. **Usage Limits**: Your account might have hit daily/monthly limits

**How to fix:**

**Option A: Check Your OpenAI Account**
1. Go to https://platform.openai.com/account/billing
2. Add a payment method (even if you stay on free tier, you often need billing info)
3. Check your usage limits at https://platform.openai.com/account/usage

**Option B: Wait and Retry**
- Free tier limits reset over time
- Wait a few minutes and try again

**Option C: Upgrade Your Plan**
- Consider upgrading if you need higher rate limits
- Check pricing at https://openai.com/pricing

#### Issue 2: Code Bug (FIXED)

**What you saw:**
```
Error executing action: DesktopEnv.step() got an unexpected keyword argument 'sleep_after_execution'
```

**What it means:**
- The code was using the wrong parameter name
- `DesktopEnv.step()` uses `pause`, not `sleep_after_execution`

**Status:** ✅ **FIXED** - Updated the code to use correct parameter

#### Issue 3: Task Failed

**Result:** `Evaluation result: 0.0`

**Why:**
- The agent returned "FAIL" because it couldn't call the API (rate limits)
- The task wasn't actually attempted

## Next Steps

### 1. Fix Rate Limiting

**Immediate Steps:**

1. **Check your OpenAI account:**
   ```bash
   # Visit in browser:
   https://platform.openai.com/account/billing
   https://platform.openai.com/account/usage
   ```

2. **Add billing information** (if needed):
   - Even free tier often requires billing info
   - No charges unless you exceed free tier

3. **Wait a bit** if you just hit limits:
   - Free tier: Wait 1-5 minutes
   - Paid tier: Usually resets faster

4. **Verify your API key works:**
   ```bash
   # Test in terminal
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
   
   Should return a list of models, not an error.

### 2. Try Again

Once rate limits are resolved, try running again:

```bash
cd /Users/rishika/OSWorld/OSWorld
python osworld_gpt4omini_agent/run_gpt4o_mini.py \
    --example evaluation_examples/examples/os/94d95f96-9699-4208-98ba-3c3119edf9c2.json \
    --output_dir ./results/test
```

### 3. Use Lower Rate Limits

If you're on free tier, you might want to add delays between requests. The agent already has retry logic with exponential backoff, but you can:

**Option A: Run during off-peak hours**
- Less competition for API access

**Option B: Reduce max_steps**
- Fewer API calls = less chance of hitting limits
```bash
python osworld_gpt4omini_agent/run_gpt4o_mini.py \
    --example ... \
    --max_steps 10 \
    --output_dir ./results/test
```

## Understanding Rate Limits

### OpenAI Free Tier Limits

- **Requests per minute**: 3-5 requests
- **Requests per day**: Limited (varies)
- **Tokens per minute**: Limited

### What This Means

- The agent needs to make **one API call per step**
- Each step = 1 screenshot analysis
- A task might need 10-30 steps
- So a task might need 10-30 API calls

### Solutions

1. **Upgrade account** - Higher limits
2. **Add delays** - Already built into retry logic
3. **Batch requests** - Not applicable here (each step needs response)
4. **Use different model** - All models have limits

## Code Fix Applied

The following bug was fixed:

**Before:**
```python
obs, reward, done, info = env.step(action, sleep_after_execution=args.sleep_after_execution)
```

**After:**
```python
obs, reward, done, info = env.step(action, pause=args.sleep_after_execution)
```

The correct parameter name is `pause`, not `sleep_after_execution`.

## Verification Checklist

Before running again, verify:

- [ ] OpenAI API key is set: `echo $OPENAI_API_KEY`
- [ ] API key is valid (test with curl above)
- [ ] Account has billing info (if required)
- [ ] Not currently rate-limited (wait if needed)
- [ ] Code bug is fixed (already done)

## Expected Behavior After Fix

Once rate limits are resolved, you should see:

1. ✅ Agent connects to OpenAI API successfully
2. ✅ Gets responses from GPT-4o-mini (not rate limit errors)
3. ✅ Agent generates pyautogui commands
4. ✅ Commands execute in the VM
5. ✅ Task makes progress (screenshots show changes)
6. ✅ Eventually completes or reaches max_steps

## Summary

**What worked:**
- ✅ Environment setup
- ✅ Agent initialization
- ✅ VM connection

**What needs fixing:**
- ⚠️ Rate limiting (add billing info, wait, or upgrade)
- ✅ Code bug (already fixed)

**Next action:**
1. Resolve rate limiting issue
2. Run again
3. Should work now!
