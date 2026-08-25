# Dead Code Confirmation \u2014 How to Verify Code Is Actually Unused

Calling code "dead" without verifying is the #1 way to embarrass yourself in code review. Reflection, runtime loading, dynamic dispatch, and aliases all hide references. Here's the rigorous process.

## The 6-step verification

Before flagging code as dead, verify through all 6:

