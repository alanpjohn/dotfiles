-- Setting the leader key
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Enable line numbers
vim.opt.number = true

-- Enable mouse mode
vim.opt.mouse = 'a'

-- Sync clipboard between OS and Neovim.
--  Schedule the setting after `UiEnter` because it can increase startup-time.
--  Remove this option if you want your OS clipboard to remain independent.
--  See `:help 'clipboard'`
vim.schedule(function()
    vim.opt.clipboard = 'unnamedplus'
end)

-- Enable break indent
vim.opt.breakindent = true

-- Save undo history
vim.opt.undofile = true

-- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
vim.opt.ignorecase = true
vim.opt.smartcase = true

-- Keep signcolumn on by default
vim.opt.signcolumn = 'yes'

-- Decrease update time
vim.opt.updatetime = 250

-- Decrease mapped sequence wait time
vim.opt.timeoutlen = 300

-- Configure how new splits should be opened
vim.opt.splitright = true
vim.opt.splitbelow = true

-- Sets how neovim will display certain whitespace characters in the editor.
--  See `:help 'list'`
--  and `:help 'listchars'`
vim.opt.list = true
vim.opt.listchars = { tab = '» ', trail = '·', nbsp = '␣' }

-- Preview substitutions live, as you type!
vim.opt.inccommand = 'split'

-- Show which line your cursor is on
vim.opt.cursorline = false

-- Minimal number of screen lines to keep above and below the cursor.
vim.opt.scrolloff = 10


-- [[ Basic Keymaps ]]
--  See `:help vim.keymap.set()`
--  See Also `:help nvim_keymap.set()

-- Clear highlights on search when pressing <Esc> in normal mode
--  See `:help hlsearch`
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')

-- Diagnostic keymaps
vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist, { desc = 'Open diagnostic [Q]uickfix list' })

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set('t', '<Esc><Esc>', '<C-\\><C-n>', { desc = 'Exit terminal mode' })

-- TIP: Disable arrow keys in normal mode
-- vim.keymap.set('n', '<left>', '<cmd>echo "Use h to move!!"<CR>')
-- vim.keymap.set('n', '<right>', '<cmd>echo "Use l to move!!"<CR>')
-- vim.keymap.set('n', '<up>', '<cmd>echo "Use k to move!!"<CR>')
-- vim.keymap.set('n', '<down>', '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
--  Use CTRL+<hjkl> to switch between windows
--
--  See `:help wincmd` for a list of all window commands
vim.keymap.set('n', '<C-h>', '<C-w><C-h>', { desc = 'Move focus to the left window' })
vim.keymap.set('n', '<C-l>', '<C-w><C-l>', { desc = 'Move focus to the right window' })
vim.keymap.set('n', '<C-j>', '<C-w><C-j>', { desc = 'Move focus to the lower window' })
vim.keymap.set('n', '<C-k>', '<C-w><C-k>', { desc = 'Move focus to the upper window' })

-- [[ Basic Autocommands ]]
--  See `:help lua-guide-autocommands`

-- Highlight when yanking (copying) text
--  Try it with `yap` in normal mode
--  See `:help vim.highlight.on_yank()`
vim.api.nvim_create_autocmd('TextYankPost', {
    desc = 'Highlight when yanking (copying) text',
    group = vim.api.nvim_create_augroup('kickstart-highlight-yank', { clear = true }),
    callback = function()
        vim.highlight.on_yank()
    end,
})

vim.o.termguicolors = false

-- [[ Install `lazy.nvim` plugin manager ]]
--    See `:help lazy.nvim.txt` or https://github.com/folke/lazy.nvim for more info
local lazypath = vim.fn.stdpath 'data' .. '/lazy/lazy.nvim'
if not (vim.uv or vim.loop).fs_stat(lazypath) then
    local lazyrepo = 'https://github.com/folke/lazy.nvim.git'
    local out = vim.fn.system { 'git', 'clone', '--filter=blob:none', '--branch=stable', lazyrepo, lazypath }
    if vim.v.shell_error ~= 0 then
        error('Error cloning lazy.nvim:\n' .. out)
    end
end ---@diagnostic disable-next-line: undefined-field
vim.opt.rtp:prepend(lazypath)

-- [[ Configure and install plugins ]]
--
--  To check the current status of your plugins, run
--    :Lazy
--
--  You can press `?` in this menu for help. Use `:q` to close the window
--
--  To update plugins you can run
--    :Lazy update
--
-- NOTE: Here is where you install your plugins.
require('lazy').setup {
    spec = {
        {
            'nvim-lua/plenary.nvim',
            lazy = true,
        },
        {
            'folke/tokyonight.nvim',
            lazy = false,
            priority = 1000,
            opts = {
                style = "night",
                transparent = true,
            },
            config = function()
                require('tokyonight').setup({
                    style = "night",
                    transparent = true,
                    on_highlights = function(hl)
                        hl.Pmenu = { bg = "none" }
                        hl.TelescopeNormal = { bg = "none" }
                    end
                })
                vim.cmd.colorscheme('tokyonight')
            end
        },
        {                       -- Useful plugin to show you pending keybinds.
            'folke/which-key.nvim',
            event = 'VimEnter', -- Sets the loading event to 'VimEnter'
            opts = {
                -- delay between pressing a key and opening which-key (milliseconds)
                -- this setting is independent of vim.opt.timeoutlen
                delay = 0,
                icons = {
                    -- set icon mappings to true if you have a Nerd Font
                    mappings = vim.g.have_nerd_font,
                    -- If you are using a Nerd Font: set icons.keys to an empty table which will use the
                    -- default which-key.nvim defined Nerd Font icons, otherwise define a string table
                    keys = vim.g.have_nerd_font and {} or {
                        Up = '<Up> ',
                        Down = '<Down> ',
                        Left = '<Left> ',
                        Right = '<Right> ',
                        C = '<C-…> ',
                        M = '<M-…> ',
                        D = '<D-…> ',
                        S = '<S-…> ',
                        CR = '<CR> ',
                        Esc = '<Esc> ',
                        ScrollWheelDown = '<ScrollWheelDown> ',
                        ScrollWheelUp = '<ScrollWheelUp> ',
                        NL = '<NL> ',
                        BS = '<BS> ',
                        Space = '<Space> ',
                        Tab = '<Tab> ',
                        F1 = '<F1>',
                        F2 = '<F2>',
                        F3 = '<F3>',
                        F4 = '<F4>',
                        F5 = '<F5>',
                        F6 = '<F6>',
                        F7 = '<F7>',
                        F8 = '<F8>',
                        F9 = '<F9>',
                        F10 = '<F10>',
                        F11 = '<F11>',
                        F12 = '<F12>',
                    },
                },

                -- Document existing key chains
                spec = {
                    { '<leader>c', group = '[C]ode',     mode = { 'n', 'x' } },
                    { '<leader>d', group = '[D]ocument' },
                    { '<leader>r', group = '[R]ename' },
                    { '<leader>s', group = '[S]earch' },
                    { '<leader>w', group = '[W]orkspace' },
                    { '<leader>t', group = '[T]oggle' },
                    { '<leader>h', group = 'Git [H]unk', mode = { 'n', 'v' } },
                },
            },
        },
        { -- Adds git related signs to the gutter, as well as utilities for managing changes
            'lewis6991/gitsigns.nvim',
            opts = {
                signs = {
                    add = { text = '+' },
                    change = { text = '~' },
                    delete = { text = '_' },
                    topdelete = { text = '‾' },
                    changedelete = { text = '~' },
                },
            },
        },
        { -- Fuzzy Finder (files, lsp, etc)
            'nvim-telescope/telescope.nvim',
            event = 'VimEnter',
            branch = '0.1.x',
            dependencies = {
                'nvim-lua/plenary.nvim',
                { -- If encountering errors, see telescope-fzf-native README for installation instructions
                    'nvim-telescope/telescope-fzf-native.nvim',

                    -- `build` is used to run some command when the plugin is installed/updated.
                    -- This is only run then, not every time Neovim starts up.
                    build = 'make',

                    -- `cond` is a condition used to determine whether this plugin should be
                    -- installed and loaded.
                    cond = function()
                        return vim.fn.executable 'make' == 1
                    end,
                },
                { 'nvim-telescope/telescope-ui-select.nvim' },

                -- Useful for getting pretty icons, but requires a Nerd Font.
                { 'nvim-tree/nvim-web-devicons',            enabled = vim.g.have_nerd_font },
            },
            config = function()
                -- Telescope is a fuzzy finder that comes with a lot of different things that
                -- it can fuzzy find! It's more than just a "file finder", it can search
                -- many different aspects of Neovim, your workspace, LSP, and more!
                --
                -- The easiest way to use Telescope, is to start by doing something like:
                --  :Telescope help_tags
                --
                -- After running this command, a window will open up and you're able to
                -- type in the prompt window. You'll see a list of `help_tags` options and
                -- a corresponding preview of the help.
                --
                -- Two important keymaps to use while in Telescope are:
                --  - Insert mode: <c-/>
                --  - Normal mode: ?
                --
                -- This opens a window that shows you all of the keymaps for the current
                -- Telescope picker. This is really useful to discover what Telescope can
                -- do as well as how to actually do it!

                -- [[ Configure Telescope ]]
                -- See `:help telescope` and `:help telescope.setup()`
                require('telescope').setup {
                    -- You can put your default mappings / updates / etc. in here
                    --  All the info you're looking for is in `:help telescope.setup()`
                    --
                    -- defaults = {
                    --   mappings = {
                    --     i = { ['<c-enter>'] = 'to_fuzzy_refine' },
                    --   },
                    -- },
                    -- pickers = {}
                    extensions = {
                        ['ui-select'] = {
                            require('telescope.themes').get_dropdown(),
                        },
                    },
                }

                -- Enable Telescope extensions if they are installed
                pcall(require('telescope').load_extension, 'fzf')
                pcall(require('telescope').load_extension, 'ui-select')

                -- See `:help telescope.builtin`
                local builtin = require 'telescope.builtin'
                vim.keymap.set('n', '<leader>sh', builtin.help_tags, { desc = '[S]earch [H]elp' })
                vim.keymap.set('n', '<leader>sk', builtin.keymaps, { desc = '[S]earch [K]eymaps' })
                vim.keymap.set('n', '<leader>sf', builtin.find_files, { desc = '[S]earch [F]iles' })
                vim.keymap.set('n', '<leader>ss', builtin.builtin, { desc = '[S]earch [S]elect Telescope' })
                vim.keymap.set('n', '<leader>sw', builtin.grep_string, { desc = '[S]earch current [W]ord' })
                vim.keymap.set('n', '<leader>sg', builtin.live_grep, { desc = '[S]earch by [G]rep' })
                vim.keymap.set('n', '<leader>sd', builtin.diagnostics, { desc = '[S]earch [D]iagnostics' })
                vim.keymap.set('n', '<leader>sr', builtin.resume, { desc = '[S]earch [R]esume' })
                vim.keymap.set('n', '<leader>s.', builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
                vim.keymap.set('n', '<leader><leader>', builtin.buffers, { desc = '[ ] Find existing buffers' })

                -- Slightly advanced example of overriding default behavior and theme
                vim.keymap.set('n', '<leader>/', function()
                    -- You can pass additional configuration to Telescope to change the theme, layout, etc.
                    builtin.current_buffer_fuzzy_find(require('telescope.themes').get_dropdown {
                        winblend = 0,
                        previewer = false,
                    })
                end, { desc = '[/] Fuzzily search in current buffer' })

                -- It's also possible to pass additional configuration options.
                --  See `:help telescope.builtin.live_grep()` for information about particular keys
                vim.keymap.set('n', '<leader>s/', function()
                    builtin.live_grep {
                        grep_open_files = true,
                        prompt_title = 'Live Grep in Open Files',
                    }
                end, { desc = '[S]earch [/] in Open Files' })

                -- Shortcut for searching your Neovim configuration files
                vim.keymap.set('n', '<leader>sn', function()
                    builtin.find_files { cwd = vim.fn.stdpath 'config' }
                end, { desc = '[S]earch [N]eovim files' })
            end,
        },
        { -- Highlight, edit, and navigate code
            'nvim-treesitter/nvim-treesitter',
            build = ':TSUpdate',
            main = 'nvim-treesitter.configs', -- Sets main module to use for opts
            -- [[ Configure Treesitter ]] See `:help nvim-treesitter`
            opts = {
                ensure_installed = { 'python', 'go', 'rust', 'yaml', 'json', 'bash', 'dockerfile' },
                -- Autoinstall languages that are not installed
                auto_install = true,
                highlight = {
                    enable = true,
                    -- Some languages depend on vim's regex highlighting system (such as Ruby) for indent rules.
                    --  If you are experiencing weird indenting issues, add the language to
                    --  the list of additional_vim_regex_highlighting and disabled languages for indent.
                    additional_vim_regex_highlighting = { 'ruby' },
                },
                indent = { enable = true, disable = { 'ruby' } },
            },
            -- There are additional nvim-treesitter modules that you can use to interact
            -- with nvim-treesitter. You should go explore a few and see what interests you:
            --
            --    - Incremental selection: Included, see `:help nvim-treesitter-incremental-selection-mod`
            --    - Show your current context: https://github.com/nvim-treesitter/nvim-treesitter-context
            --    - Treesitter + textobjects: https://github.com/nvim-treesitter/nvim-treesitter-textobjects
        },
        {
            'neovim/nvim-lspconfig',
            dependencies = {
                { 'j-hui/fidget.nvim',                        opts = {} },
                { 'hrsh7th/cmp-nvim-lsp' },
                { 'williamboman/mason.nvim',                  opts = {} },
                { 'williamboman/mason-lspconfig.nvim' },
                { 'WhoIsSethDaniel/mason-tool-installer.nvim' },
                {
                    'diogo464/kubernetes.nvim',
                    opts = {
                        -- this can help with autocomplete. it sets the `additionalProperties` field on type definitions to false if it is not already present.
                        schema_strict = true,
                        -- true:  generate the schema every time the plugin starts
                        -- false: only generate the schema if the files don't already exists. run `:KubernetesGenerateSchema` manually to generate the schema if needed.
                        schema_generate_always = true,
                        -- Patch yaml-language-server's validation.js file.
                        patch = true,
                    }
                },
            },

            config = function()
                vim.api.nvim_create_autocmd('LspAttach', {
                    group = vim.api.nvim_create_augroup('kickstart-lsp-attach', { clear = true }),
                    callback = function(event)
                        local map = function(keys, func, desc, mode)
                            mode = mode or 'n'
                            vim.keymap.set(mode, keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
                        end

                        map('gd', require('telescope.builtin').lsp_definitions, '[G]oto [D]efinition')
                        map('gr', require('telescope.builtin').lsp_references, '[G]oto [R]eferences')
                        map('gI', require('telescope.builtin').lsp_implementations, '[G]oto [I]mplementation')
                        map('<leader>D', require('telescope.builtin').lsp_type_definitions, 'Type [D]efinition')
                        map('<leader>ds', require('telescope.builtin').lsp_document_symbols, '[D]ocument [S]ymbols')
                        map('<leader>ws', require('telescope.builtin').lsp_dynamic_workspace_symbols,
                            '[W]orkspace [S]ymbols')
                        map('<leader>rn', vim.lsp.buf.rename, '[R]e[n]ame')
                        map('<leader>ca', vim.lsp.buf.code_action, '[C]ode [A]ction')
                        map('gD', vim.lsp.buf.declaration, '[G]oto [D]eclaration')

                        local client = vim.lsp.get_client_by_id(event.data.client_id)
                        if client and client.methods and client.supports_method(vim.lsp.protocol.methods.textDocument.documentHighlight) then
                            local highlight_augroup = vim.api.nvim_create_augroup('LspDocumentHighlight',
                                { clear = true })
                            vim.api.nvim_create_autocmd('CursorHold', {
                                buffer = event.buf,
                                callback = vim.lsp.buf.document_highlight,
                                group = highlight_augroup,
                            })

                            vim.api.nvim_create_autocmd('CursorMoved', {
                                buffer = event.buf,
                                group = highlight_augroup,
                                callback = vim.lsp.buf.clear_references,
                            })

                            vim.api.nvim_create_autocmd('LspDetach', {
                                group = vim.api.nvim_create_augroup('kickstart-lsp-detach', { clear = true }),
                                callback = function()
                                    vim.lsp.buf.clear_references()
                                    vim.api.nvim_clear_autocmds { group = 'kickstart-lsp-highlight', buffer = event.buf }
                                end,
                            })
                        end
                        if client and client:supports_method(vim.lsp.protocol.Methods.textDocument_inlayHint) then
                            map('<leader>th', function()
                                vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = event.buf })
                            end, '[T]oggle Inlay [H]ints')
                        end
                    end,
                })

                local capabilities = vim.lsp.protocol.make_client_capabilities()
                capabilities = vim.tbl_deep_extend('force', capabilities,
                    require('cmp_nvim_lsp').default_capabilities(capabilities))

                local servers = {
                    clangd = {},
                    pyright = {},
                    pyrefly = {},
                    ruff = {},
                    gopls = {},
                    yamlls = {
                        settings = {
                            yaml = {
                                schemas = {
                                    [require('kubernetes').yamlls_schema()] = "*.yaml",
                                    ["http://json.schemastore.org/github-workflow"] = ".github/workflows/*",
                                    ["http://json.schemastore.org/github-action"] = ".github/action.{yml,yaml}",
                                    ["http://json.schemastore.org/ansible-stable-2.9"] = "roles/tasks/*.{yml,yaml}",
                                    ["http://json.schemastore.org/prettierrc"] = ".prettierrc.{yml,yaml}",
                                    ["http://json.schemastore.org/kustomization"] = "kustomization.{yml,yaml}",
                                    ["http://json.schemastore.org/ansible-playbook"] = "*play*.{yml,yaml}",
                                    ["http://json.schemastore.org/chart"] = "Chart.{yml,yaml}",
                                    ["https://json.schemastore.org/dependabot-v2"] = ".github/dependabot.{yml,yaml}",
                                    ["https://json.schemastore.org/gitlab-ci"] = "*gitlab-ci*.{yml,yaml}",
                                    ["https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/schemas/v3.1/schema.json"] =
                                    "*api*.{yml,yaml}",
                                    ["https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json"] =
                                    "*docker-compose*.{yml,yaml}",
                                    ["https://raw.githubusercontent.com/argoproj/argo-workflows/master/api/jsonschema/schema.json"] =
                                    "*flow*.{yml,yaml}",
                                },
                            }
                        }
                    },
                    rust_analyzer = {},
                    dockerls = {},
                    jsonls = {},
                    bashls = {},
                }

                local ensure_installed = vim.tbl_keys(servers or {})
                vim.list_extend(ensure_installed, {
                    'stylua', -- Used to format Lua code
                })
                require('mason-tool-installer').setup { ensure_installed = ensure_installed }

                require('mason-lspconfig').setup {
                    ensure_installed = ensure_installed
                }

                for name, server in pairs(servers) do
                    server.capabilities = vim.tbl_deep_extend('force', {}, capabilities,
                        server.capabilities or {})
                    vim.lsp.config(name, server)
                end
            end
        },
        { -- Autoformat
            'stevearc/conform.nvim',
            event = { 'BufWritePre' },
            cmd = { 'ConformInfo' },
            keys = {
                {
                    '<leader>f',
                    function()
                        require('conform').format { async = true, lsp_format = 'fallback' }
                    end,
                    mode = '',
                    desc = '[F]ormat buffer',
                },
            },
            opts = {
                notify_on_error = false,
                format_on_save = function(bufnr)
                    -- Disable "format_on_save lsp_fallback" for languages that don't
                    -- have a well standardized coding style. You can add additional
                    -- languages here or re-enable it for the disabled ones.
                    local disable_filetypes = { c = true, cpp = true }
                    local lsp_format_opt
                    if disable_filetypes[vim.bo[bufnr].filetype] then
                        lsp_format_opt = 'never'
                    else
                        lsp_format_opt = 'fallback'
                    end
                    return {
                        timeout_ms = 500,
                        lsp_format = lsp_format_opt,
                    }
                end,
                formatters_by_ft = {
                    lua = { 'stylua' },
                    -- Conform can also run multiple formatters sequentially
                    -- python = { "isort", "black" },
                    --
                    -- You can use 'stop_after_first' to run the first available formatter from the list
                    -- javascript = { "prettierd", "prettier", stop_after_first = true },
                },
            },
        },

        { -- Autocompletion
            'hrsh7th/nvim-cmp',
            event = 'InsertEnter',
            dependencies = {
                -- Snippet Engine & its associated nvim-cmp source
                {
                    'L3MON4D3/LuaSnip',
                    build = (function()
                        -- Build Step is needed for regex support in snippets.
                        -- This step is not supported in many windows environments.
                        -- Remove the below condition to re-enable on windows.
                        if vim.fn.has 'win32' == 1 or vim.fn.executable 'make' == 0 then
                            return
                        end
                        return 'make install_jsregexp'
                    end)(),
                    dependencies = {
                        -- `friendly-snippets` contains a variety of premade snippets.
                        --    See the README about individual language/framework/plugin snippets:
                        --    https://github.com/rafamadriz/friendly-snippets
                        -- {
                        --   'rafamadriz/friendly-snippets',
                        --   config = function()
                        --     require('luasnip.loaders.from_vscode').lazy_load()
                        --   end,
                        -- },
                    },
                },
                'saadparwaiz1/cmp_luasnip',

                -- Adds other completion capabilities.
                --  nvim-cmp does not ship with all sources by default. They are split
                --  into multiple repos for maintenance purposes.
                'hrsh7th/cmp-nvim-lsp',
                'hrsh7th/cmp-path',
            },
            config = function()
                -- See `:help cmp`
                local cmp = require 'cmp'
                local luasnip = require 'luasnip'
                luasnip.config.setup {}

                cmp.setup {
                    snippet = {
                        expand = function(args)
                            luasnip.lsp_expand(args.body)
                        end,
                    },
                    completion = { completeopt = 'menu,menuone,noinsert' },

                    -- For an understanding of why these mappings were
                    -- chosen, you will need to read `:help ins-completion`
                    --
                    -- No, but seriously. Please read `:help ins-completion`, it is really good!
                    mapping = cmp.mapping.preset.insert {
                        -- Select the [n]ext item
                        ['<C-n>'] = cmp.mapping.select_next_item(),
                        -- Select the [p]revious item
                        ['<C-p>'] = cmp.mapping.select_prev_item(),

                        -- Scroll the documentation window [b]ack / [f]orward
                        ['<C-b>'] = cmp.mapping.scroll_docs(-4),
                        ['<C-f>'] = cmp.mapping.scroll_docs(4),

                        -- Accept ([y]es) the completion.
                        --  This will auto-import if your LSP supports it.
                        --  This will expand snippets if the LSP sent a snippet.
                        ['<C-y>'] = cmp.mapping.confirm { select = true },

                        -- If you prefer more traditional completion keymaps,
                        -- you can uncomment the following lines
                        --['<CR>'] = cmp.mapping.confirm { select = true },
                        --['<Tab>'] = cmp.mapping.select_next_item(),
                        --['<S-Tab>'] = cmp.mapping.select_prev_item(),

                        -- Manually trigger a completion from nvim-cmp.
                        --  Generally you don't need this, because nvim-cmp will display
                        --  completions whenever it has completion options available.
                        ['<C-Space>'] = cmp.mapping.complete {},

                        -- Think of <c-l> as moving to the right of your snippet expansion.
                        --  So if you have a snippet that's like:
                        --  function $name($args)
                        --    $body
                        --  end
                        --
                        -- <c-l> will move you to the right of each of the expansion locations.
                        -- <c-h> is similar, except moving you backwards.
                        ['<C-l>'] = cmp.mapping(function()
                            if luasnip.expand_or_locally_jumpable() then
                                luasnip.expand_or_jump()
                            end
                        end, { 'i', 's' }),
                        ['<C-h>'] = cmp.mapping(function()
                            if luasnip.locally_jumpable(-1) then
                                luasnip.jump(-1)
                            end
                        end, { 'i', 's' }),

                        -- For more advanced Luasnip keymaps (e.g. selecting choice nodes, expansion) see:
                        --    https://github.com/L3MON4D3/LuaSnip?tab=readme-ov-file#keymaps
                    },
                    sources = {
                        {
                            name = 'lazydev',
                            -- set group index to 0 to skip loading LuaLS completions as lazydev recommends it
                            group_index = 0,
                        },
                        { name = 'nvim_lsp' },
                        { name = 'luasnip' },
                        { name = 'path' },
                    },
                }
            end,
        },

        -- Highlight todo, notes, etc in comments
        {
            'folke/todo-comments.nvim',
            event = 'VimEnter',
            dependencies = { 'nvim-lua/plenary.nvim' },
            opts = { signs = false },
        },

        {
            'nvim-neo-tree/neo-tree.nvim',
            version = '*',
            dependencies = {
                'nvim-lua/plenary.nvim',
                'nvim-tree/nvim-web-devicons', -- not strictly required, but recommended
                'MunifTanjim/nui.nvim',
            },
            cmd = 'Neotree',
            init = function()
                vim.api.nvim_create_autocmd('BufEnter', {
                    -- make a group to be able to delete it later
                    group = vim.api.nvim_create_augroup('NeoTreeInit', { clear = true }),
                    callback = function()
                        local f = vim.fn.expand '%:p'
                        if vim.fn.isdirectory(f) ~= 0 then
                            vim.cmd('Neotree current dir=' .. f)
                            -- neo-tree is loaded now, delete the init autocmd
                            vim.api.nvim_clear_autocmds { group = 'NeoTreeInit' }
                        end
                    end,
                })
                -- keymaps
            end,
            keys = {
                { '\\', ':Neotree reveal<CR>', desc = 'NeoTree reveal', silent = true },
            },
            opts = {
                filesystem = {
                    hijack_netrw_behavior = 'open_current',
                    window = {
                        mappings = {
                            ['\\'] = 'close_window',
                        },
                    },
                },
            },
        },
    },

    checker = {
        enabled = true,
    },
}
