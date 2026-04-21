{
  description = "Claude Code dev shell via sadjow flake";

  inputs = {
    nixpkgs.url     = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    claude-code.url = "github:sadjow/claude-code-nix";
  };

  outputs = { self, nixpkgs, flake-utils, claude-code }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in {
        devShells.default = pkgs.mkShell {
          name = "claude-code";

          packages = [
            claude-code.packages.${system}.default
            pkgs.git
            pkgs.ripgrep
            pkgs.fd
            pkgs.nodejs
            pkgs.vscode
          ];

          shellHook = ''
            echo "Claude Code $(claude --version) ready"
            if [ -z "''${ANTHROPIC_API_KEY:-}" ]; then
              echo "⚠  Set ANTHROPIC_API_KEY before running claude"
            fi
          '';

          ANTHROPIC_API_KEY = builtins.getEnv "ANTHROPIC_API_KEY";
        };
      });
}
