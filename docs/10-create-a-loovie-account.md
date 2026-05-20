# Create a Loovie account

You need a Loovie account to use BYO, because the iOS app is the thing that calls your server. There is no web signup right now; everything happens in the iOS app.

> **Heads up:** Loovie is currently iOS only (iPhone + iPad). There is no Android version.

## Steps

1. **Install Loovie from the App Store.** [Open in the App Store](https://apps.apple.com/app/loovie), or search for *Loovie* in the App Store on your iPhone or iPad.
2. **Open the app.** On the sign-up screen you have three choices:
   - **Continue with Apple**: fastest, no email required, recommended.
   - **Continue with Google**: uses your Google account.
   - **Continue with email**: Loovie emails you a one-time code; tap the magic link or enter the code.
3. **Free credits arrive automatically.** You do not need them for BYO (BYO is free in the app), but you need an account either way so your generations and your library are tied to a user.
4. **Join the BYO beta.** Open *Preferences* and tap *Local Compute (BYO), join the beta*. This unlocks the BYO server settings and the *Your server (BYO)* tier in the image and video quality pickers. The change takes effect on the next app start; if you do not see the BYO entries, force-quit and reopen Loovie.

## After signup

- The **BYO server** entry appears under *Preferences → Connected apps & MCP* once you are enrolled in the beta. [Configure it](60-configure-the-app.md) with your server URL and bearer token.
- Your account has nothing to do with your BYO server, your server URL and bearer token never leave the device. See [`50-security-and-tokens.md`](50-security-and-tokens.md).

## What if I cannot install the iOS app?

Right now, the beta requires iOS. We will document any future paths (web, Mac Catalyst) here when they exist. The contract is open, so you can still run a Loovie-compatible server and have it ready for the day a non-iOS client appears.

## Beta is opt-in but free

- Free in the app while you are in the beta. No subscription, no credits required.
- After beta, the BYO interface becomes a flat-fee "BYO Pass" subscription. Generations themselves stay 0 credits forever. We will publish the price and timing in the changelog and on `loovie.app/byo` well before that switches on.
- RunPod or any other compute provider you use bills you separately. Loovie does not charge for BYO generations.
