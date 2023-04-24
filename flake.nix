# Flake
{ description = "Telegram Backup TGC";
  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
             flake-utils.url = "github:numtide/flake-utils"; };

  outputs = { self, nixpkgs, flake-utils }: flake-utils.lib.eachDefaultSystem (system:
    let pkgs = nixpkgs.legacyPackages.${system};

        hypy_utils = { lib, python3Packages, fetchFromGitHub }:
          python3Packages.buildPythonApplication {
            pname = "hypy_utils";
            version = "1.0.18";
            src = fetchFromGitHub { owner = "hykilpikonna";
                                    repo = "HyPyUtils";
                                    rev = "332a63479e8e88ba3edafa342e7010e6fac8cf8a";
                                    sha256 = "sha256-w4dRY2vv6dvtIOCNfIW6AXp4iuvUfNM7RY8Cn6YeTJ0="; };
            propagatedBuildInputs = with python3Packages; [ setuptools tqdm numpy matplotlib numba requests ];
            meta = { description = "HyDEV Utils for Python | Mostly for personal use";
                     homepage = "https://github.com/hykilpikonna/HyPyUtils";
                     license = lib.licenses.mit; }; };

        tgcDrv = { lib, pkgs, python3Packages }:
          python3Packages.buildPythonPackage {
            pname = "tgc";
            version = "unstable";
            src = self;
            format = "pyproject";
            buildInputs = with pkgs; [ puppeteer-cli ];
            propagatedBuildInputs = (with python3Packages;
              [ setuptools
                toml
                pyrogram
                tgcrypto
                uvloop
                requests
                pillow
                feedgen
                markdown
                importlib-metadata ])
            ++ [ (pkgs.callPackage hypy_utils {}) ];
            preInstall = ''
              # Move the submodules
              mkdir -p $out/${python3Packages.python.sitePackages}
              mv tgc $out/${python3Packages.python.sitePackages}
            '';
            meta = { description = "Telegram adapter for tg-blog.";
                     longDescription = ''
                       This is the Telegram adapter for tg-blog, a front-end for displaying
                       telegram (or any compatible) channel data as an interactive web page.
                       See also: github:one-among-us/tg-blog
                     '';
                     homepage = "https://github.com/one-among-us/TelegramBackup";
                     license = lib.licenses.mit;
                     mainProgram = "tgc"; }; };
    in  { packages = rec {
            default = tgc;
            tgc = pkgs.callPackage tgcDrv {}; };
          devShells.default = pkgs.mkShell {
            packages = [ (pkgs.python3.withPackages (p: [ self.packages.tgc ])) ]; };});}
