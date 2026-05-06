source /usr/share/cachyos-fish-config/cachyos-config.fish

# overwrite greeting
# potentially disabling fastfetch
function fish_greeting
end

starship init fish | source

set -x EDITOR nvim

if status is-interactive
    atuin init fish | source
end
