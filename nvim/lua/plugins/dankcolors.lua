return {
	{
		"RRethy/base16-nvim",
		priority = 1000,
		config = function()
			require('base16-colorscheme').setup({
				base00 = '#171310',
				base01 = '#171310',
				base02 = '#9d9792',
				base03 = '#9d9792',
				base04 = '#fff6ef',
				base05 = '#fffbf8',
				base06 = '#fffbf8',
				base07 = '#fffbf8',
				base08 = '#ffa49f',
				base09 = '#ffa49f',
				base0A = '#ffcda7',
				base0B = '#b5ffa5',
				base0C = '#ffe4d0',
				base0D = '#ffcda7',
				base0E = '#ffd5b7',
				base0F = '#ffd5b7',
			})

			vim.api.nvim_set_hl(0, 'Visual', {
				bg = '#9d9792',
				fg = '#fffbf8',
				bold = true
			})
			vim.api.nvim_set_hl(0, 'Statusline', {
				bg = '#ffcda7',
				fg = '#171310',
			})
			vim.api.nvim_set_hl(0, 'LineNr', { fg = '#9d9792' })
			vim.api.nvim_set_hl(0, 'CursorLineNr', { fg = '#ffe4d0', bold = true })

			vim.api.nvim_set_hl(0, 'Statement', {
				fg = '#ffd5b7',
				bold = true
			})
			vim.api.nvim_set_hl(0, 'Keyword', { link = 'Statement' })
			vim.api.nvim_set_hl(0, 'Repeat', { link = 'Statement' })
			vim.api.nvim_set_hl(0, 'Conditional', { link = 'Statement' })

			vim.api.nvim_set_hl(0, 'Function', {
				fg = '#ffcda7',
				bold = true
			})
			vim.api.nvim_set_hl(0, 'Macro', {
				fg = '#ffcda7',
				italic = true
			})
			vim.api.nvim_set_hl(0, '@function.macro', { link = 'Macro' })

			vim.api.nvim_set_hl(0, 'Type', {
				fg = '#ffe4d0',
				bold = true,
				italic = true
			})
			vim.api.nvim_set_hl(0, 'Structure', { link = 'Type' })

			vim.api.nvim_set_hl(0, 'String', {
				fg = '#b5ffa5',
				italic = true
			})

			vim.api.nvim_set_hl(0, 'Operator', { fg = '#fff6ef' })
			vim.api.nvim_set_hl(0, 'Delimiter', { fg = '#fff6ef' })
			vim.api.nvim_set_hl(0, '@punctuation.bracket', { link = 'Delimiter' })
			vim.api.nvim_set_hl(0, '@punctuation.delimiter', { link = 'Delimiter' })

			vim.api.nvim_set_hl(0, 'Comment', {
				fg = '#9d9792',
				italic = true
			})

			local current_file_path = vim.fn.stdpath("config") .. "/lua/plugins/dankcolors.lua"
			if not _G._matugen_theme_watcher then
				local uv = vim.uv or vim.loop
				_G._matugen_theme_watcher = uv.new_fs_event()
				_G._matugen_theme_watcher:start(current_file_path, {}, vim.schedule_wrap(function()
					local new_spec = dofile(current_file_path)
					if new_spec and new_spec[1] and new_spec[1].config then
						new_spec[1].config()
						print("Theme reload")
					end
				end))
			end
		end
	}
}
