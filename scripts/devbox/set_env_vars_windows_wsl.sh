export NIX_LD_LIBRARY_PATH=${PWD}/.devbox/nix/profile/default/lib/:${NIX_LD_LIBRARY_PATH:-}
export LD_LIBRARY_PATH=${PWD}/.devbox/nix/profile/default/lib/:${LD_LIBRARY_PATH:-}
export BROWSER=wslview  # Use wslview to open URLs in the default browser
