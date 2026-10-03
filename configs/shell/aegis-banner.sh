# AegisOS login banner (installed to /etc/profile.d/aegis-banner.sh)
case "$-" in
  *i*) command -v aegis >/dev/null 2>&1 && aegis banner 2>/dev/null ;;
esac
