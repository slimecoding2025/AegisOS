# Website

`website/index.html` is the whole site (one self-contained file, no build step) and `website/vercel.json` sets
basic security headers. Deploy on Vercel by importing the GitHub repository and setting **Root Directory** to
`website`; no framework preset and no build command are needed.

The Download section reads `https://api.github.com/repos/slimecoding2025/AegisOS/releases` in the visitor's
browser and lists releases and their assets. If there is no release, or the request fails, it shows an honest
empty state. Unauthenticated GitHub API requests are rate limited per visitor IP.

When a custom domain is bought, update: the Vercel project domain settings, the contact section of the page, and
`HOME_URL` in `build/config/hooks/live/0100-aegis-os-release.hook.chroot`.
