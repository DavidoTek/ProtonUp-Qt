{
  description = "ProtonUp-Qt — GUI tool to install/manage Wine/Proton compatibility tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }: let
    inherit (nixpkgs) lib;
    forAllSystems = lib.genAttrs [ "x86_64-linux" ];

    workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };

    pythonSets = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python312;
    in
      (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope (
        lib.composeManyExtensions [
          pyproject-build-systems.overlays.wheel
          overlay
          (final: prev: {
            pyside6-essentials = pkgs.python312Packages.pyside6;
            shiboken6 = pkgs.python312Packages.shiboken6;
            steam = prev.steam.overrideAttrs (old: {
              nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ final.setuptools final.wheel ];
            });
            vdf = prev.vdf.overrideAttrs (old: {
              nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ final.setuptools final.wheel ];
            });
          })
        ]
      )
    );
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonSet = pythonSets.${system};
      protonup-qt-env = pythonSet.mkVirtualEnv "protonup-qt-env" (workspace.deps.default // {
        shiboken6 = [ ];
      });

      appdir = pkgs.runCommand "ProtonUp-Qt.AppDir" {
        nativeBuildInputs = [ pkgs.python312 ];
      } ''
        set -euo pipefail

        mkdir -p "$out/usr"
        cp -rL ${protonup-qt-env}/* "$out/usr/"
        chmod -R u+w "$out"

        mkdir -p "$out/usr/share"
        cp -rL ${./share}/* "$out/usr/share/"

        rm -rf "$out/usr/lib/python3.12/site-packages/PySide6/Qt/qml/"
        rm -f "$out/usr/lib/python3.12/site-packages/PySide6/"{assistant,designer,linguist,lrelease,lupdate}
        rm -f "$out/usr/lib/python3.12/site-packages/PySide6/"{Qt3D*,QtBluetooth*,QtCharts*,QtConcurrent*,QtDataVisualization*,QtDesigner*,QtHelp*,QtMultimedia*,QtNetwork*,QtOpenGL*,QtPositioning*,QtPrintSupport*,QtQml*,QtQuick*,QtRemoteObjects*,QtScxml*,QtSensors*,QtSerialPort*,QtSql*,QtStateMachine*,QtSvg*,QtTest*,QtWeb*,QtXml*}

        mkdir -p "$out/usr/bin"
        cat > "$out/AppRun" << 'RUNNER'
        #!/bin/bash
        APPDIR="$(dirname "$(readlink -f "$0")")"
        export PYTHONPATH="''${APPDIR}/usr/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"
        export QT_PLUGIN_PATH="''${APPDIR}/usr/lib/python3.12/site-packages/PySide6/Qt/plugins"
        exec "''${APPDIR}/usr/bin/python3" -m pupgui2 "$@"
        RUNNER
        chmod +x "$out/AppRun"

        cp "$out/usr/share/applications/net.davidotek.pupgui2.desktop" "$out/"
        cp "$out/usr/share/icons/hicolor/256x256/apps/net.davidotek.pupgui2.png" "$out/"
      '';

      appimagetool = pkgs.fetchurl {
        url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage";
        hash = "sha256-uQ9KixiWdUX9p4pEWydoChZC8e+UiM7Si2U5jyvnrdI=";
      };

      appimagetool-extracted = pkgs.runCommand "appimagetool-extracted" {
        nativeBuildInputs = [ pkgs.squashfsTools pkgs.binutils-unwrapped ];
      } ''
        offset=$(LC_ALL=C readelf -h ${appimagetool} | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')
        unsquashfs -d "$out" -o "$offset" ${appimagetool}
      '';
    in {
      default = protonup-qt-env;

      appimage = pkgs.runCommand "ProtonUp-Qt-${protonup-qt-env.name}-x86_64.AppImage" {
        nativeBuildInputs = [ pkgs.squashfsTools pkgs.binutils-unwrapped ];
      } ''
        set -euo pipefail

        runtime_offset=$(LC_ALL=C readelf -h ${appimagetool} | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')

        head -c "$runtime_offset" ${appimagetool} > $PWD/runtime
        chmod +x $PWD/runtime

        mksquashfs ${appdir} $PWD/appimage.squashfs -noappend -comp xz

        cat $PWD/runtime $PWD/appimage.squashfs > $out
        chmod +x $out
      '';
    });

    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonSet = pythonSets.${system};
      virtualenv = pythonSet.mkVirtualEnv "protonup-qt-dev-env" workspace.deps.all;
    in {
      default = pkgs.mkShell {
        packages = [
          virtualenv
          pkgs.uv
        ];
        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = pythonSet.python.interpreter;
          UV_PYTHON_DOWNLOADS = "never";
        };
        shellHook = ''
          unset PYTHONPATH
        '';
      };
    });

    apps = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      app = pkgs.writeShellApplication {
        name = "protonup-qt";
        runtimeInputs = [ self.packages.${system}.default ];
        text = ''exec python -m pupgui2 "$@"'';
      };
    in {
      default = {
        type = "app";
        program = "${app}/bin/protonup-qt";
      };
    });
  };
}
