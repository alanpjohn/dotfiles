source /usr/share/cachyos-fish-config/cachyos-config.fish

# overwrite greeting
# potentially disabling fastfetch
function fish_greeting
end

starship init fish | source

set -x EDITOR nvim

# Dotfiles CLI repo location
set -x DOTFILES_REPO_DIR ~/Documents/dotfiles
