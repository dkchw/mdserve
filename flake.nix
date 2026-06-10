{
  description = "A beautiful local file server with Markdown rendering";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgsFor.${system};
        in
        {
          mdserve = pkgs.python3Packages.buildPythonApplication {
            pname = "mdserve";
            version = "1.0.0";
            pyproject = true;

            src = ./.;

            build-system = [
              pkgs.python3Packages.hatchling
            ];

            dependencies = [
              pkgs.python3Packages.markdown
              pkgs.python3Packages.pygments
            ];

            doCheck = false;
          };
          default = self.packages.${system}.mdserve;
        });

      overlays.default = final: prev: {
        mdserve = self.packages.${final.system}.mdserve;
      };

      homeManagerModules.mdserve = { config, lib, pkgs, ... }:
        let
          cfg = config.services.mdserve;
        in
        {
          options.services.mdserve = {
            enable = lib.mkEnableOption "mdserve local file server";
            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${pkgs.system}.mdserve;
              defaultText = lib.literalExpression "inputs.self.packages.\${pkgs.system}.mdserve";
              description = "The mdserve package to use.";
            };
            port = lib.mkOption {
              type = lib.types.port;
              default = 2112;
              description = "Port to listen on.";
            };
            bind = lib.mkOption {
              type = lib.types.str;
              default = "127.0.0.1";
              description = "Address to bind to (e.g. 127.0.0.1 or 0.0.0.0).";
            };
            workingDirectory = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "Working directory from which to serve files (defaults to home directory).";
            };
          };

          config = lib.mkIf cfg.enable {
            home.packages = [ cfg.package ];

            systemd.user.services.mdserve = lib.mkIf pkgs.stdenv.isLinux {
              Unit = {
                Description = "mdserve Markdown file server";
                After = [ "network.target" ];
              };
              Service = {
                ExecStart = "${cfg.package}/bin/mdserve ${toString cfg.port}"
                  + (lib.optionalString (cfg.bind != "") " --bind ${cfg.bind}");
                Restart = "on-failure";
              } // (lib.optionalAttrs (cfg.workingDirectory != null) {
                WorkingDirectory = cfg.workingDirectory;
              });
              Install = {
                WantedBy = [ "default.target" ];
              };
            };
          };
        };

      homeManagerModules.default = self.homeManagerModules.mdserve;
    };
}
