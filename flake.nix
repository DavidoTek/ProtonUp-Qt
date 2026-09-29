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

    # Fixes for git dependencies that ship without a declared build system.
    buildFixes = final: prev: {
      steam = prev.steam.overrideAttrs (old: {
        nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ final.setuptools final.wheel ];
      });
      vdf = prev.vdf.overrideAttrs (old: {
        nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ final.setuptools final.wheel ];
      });
    };

    mkPythonSet = pkgs: extraOverlays:
      (pkgs.callPackage pyproject-nix.build.packages { python = pkgs.python312; }).overrideScope (
        lib.composeManyExtensions ([
          pyproject-build-systems.overlays.wheel
          overlay
          buildFixes
        ] ++ extraOverlays)
      );

    # Python set for running on Nix: PySide6 comes from nixpkgs, linked against the Nix Qt.
    pythonSets = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in
      mkPythonSet pkgs [
        (final: prev: {
          pyside6-essentials = pkgs.python312Packages.pyside6;
          shiboken6 = pkgs.python312Packages.shiboken6;
        })
      ]
    );

    # Python set for the AppImage: the unmodified manylinux wheels from PyPI, which bundle
    # their own Qt and only depend on libraries found on common desktop systems.
    # ELF fixups (autoPatchelf, RPATH shrinking, stripping) are disabled so the binaries stay
    # exactly as shipped by upstream and never reference /nix/store.
    appimagePythonSets = forAllSystems (system: mkPythonSet nixpkgs.legacyPackages.${system} [
      (final: prev: lib.mapAttrs (name: pkg:
        if lib.isDerivation pkg && pkg ? overrideAttrs then
          pkg.overrideAttrs { dontAutoPatchelf = true; dontPatchELF = true; dontStrip = true; }
        else pkg
      ) prev)
    ]);
  in {
    packages = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      pythonSet = pythonSets.${system};
      protonup-qt-env = pythonSet.mkVirtualEnv "protonup-qt-env" (workspace.deps.default // {
        shiboken6 = [ ];
      });

      version = (lib.importTOML ./pyproject.toml).project.version;
      appimageName = "ProtonUp-Qt-${version}-x86_64.AppImage";
      updateInformation = "gh-releases-zsync|DavidoTek|ProtonUp-Qt|latest|ProtonUp-Qt-*x86_64.AppImage.zsync";

      appimage-env = appimagePythonSets.${system}.mkVirtualEnv "protonup-qt-appimage-env" workspace.deps.default;

      # Relocatable CPython that only depends on glibc >= 2.17
      python-standalone = pkgs.fetchurl {
        url = "https://github.com/astral-sh/python-build-standalone/releases/download/20260929/cpython-3.12.14%2B20260929-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz";
        hash = "sha256-72BSAPgXTofs/DCOUqiBJ1Q/hd1clA3F6SyrJEuYoAM=";
      };

      # Needed by the Qt xcb platform plugin, but not installed by default on GNOME-based distributions
      libxcb-cursor-deb = pkgs.fetchurl {
        urls = [
          "http://archive.ubuntu.com/ubuntu/pool/universe/x/xcb-util-cursor/libxcb-cursor0_0.1.1-4ubuntu1_amd64.deb"
          "https://snapshot.ubuntu.com/ubuntu/20240101T000000Z/pool/universe/x/xcb-util-cursor/libxcb-cursor0_0.1.1-4ubuntu1_amd64.deb"
        ];
        hash = "sha256-ybXRrUr1c5exvXfgqSdQ40QZ3vE0wCgqCDaunvwHz2Q=";
      };

      # Static AppImage type 2 runtime (does not require libfuse2 on the host)
      appimage-runtime = pkgs.fetchurl {
        url = "https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64";
        hash = "sha256-L8qLRDySUQ8Ug6iD9gBhrQm0a5eLJjHIB82HOkfsJg0=";
      };

      appdir = pkgs.runCommand "ProtonUp-Qt.AppDir" {
        nativeBuildInputs = [ pkgs.python312 pkgs.binutils-unwrapped pkgs.dpkg ];
      } ''
        set -euo pipefail
        usr="$out/usr"
        site="$usr/lib/python3.12/site-packages"

        # Python interpreter and standard library
        mkdir -p "$usr"
        tar -xzf ${python-standalone} -C "$usr" --strip-components=1
        chmod -R u+w "$out"
        # python3.12 is statically linked against libpython
        rm -rf "$usr"/{include,share} "$usr"/lib/{libpython3*,pkgconfig,tcl*,tk*,itcl*,thread*}
        find "$usr/bin" -mindepth 1 ! -name python3 ! -name python3.12 -delete
        rm -rf "$usr"/lib/python3.12/{config-3.12-*,ensurepip,idlelib,lib2to3,tkinter,turtledemo,turtle.py,site-packages}
        rm -f "$usr"/lib/python3.12/lib-dynload/_tkinter*

        # Python packages from the manylinux wheels in uv.lock
        cp -rL --preserve=timestamps ${appimage-env}/lib/python3.12/site-packages "$site"
        chmod -R u+w "$site"
        rm -rf "$site/tests"
        python3 ${./nix/prune-pyside6.py} "$site"

        # Found by libQt6XcbQpa through its RUNPATH ($ORIGIN)
        dpkg-deb --fsys-tarfile ${libxcb-cursor-deb} \
          | tar -x --wildcards -O './usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0.*' > "$site/PySide6/Qt/lib/libxcb-cursor.so.0"

        # Pre-compile bytecode, as the AppImage is read-only at runtime.
        # -s left-strips $usr so no /nix/store path ends up in co_filename.
        find "$usr/lib/python3.12" -name __pycache__ -type d -prune -exec rm -rf {} +
        python3 -m compileall -q -j 0 -s "$usr" --invalidation-mode unchecked-hash "$usr/lib/python3.12" >/dev/null

        # Guard: nothing may reference the Nix store
        if grep -rlF /nix/store "$out" --include='*.so*' --include='python3*' --include='*.pyc' | grep .; then
          echo "error: AppDir contains references to /nix/store" >&2
          exit 1
        fi

        mkdir -p "$usr/share"
        cp -r ${./share}/* "$usr/share/"
        cp ${./share/applications/net.davidotek.pupgui2.desktop} "$out/net.davidotek.pupgui2.desktop"
        cp ${./share/icons/hicolor/256x256/apps/net.davidotek.pupgui2.png} "$out/net.davidotek.pupgui2.png"
        ln -s net.davidotek.pupgui2.png "$out/.DirIcon"

        cat > "$out/AppRun" << 'EOF'
        #!/bin/sh
        HERE="$(dirname "$(readlink -f "$0")")"
        exec "$HERE/usr/bin/python3" -I -m pupgui2 "$@"
        EOF
        chmod +x "$out/AppRun"
      '';
    in {
      default = protonup-qt-env;

      inherit appdir;

      # Directory containing the AppImage and its .zsync file for AppImageUpdate
      appimage = pkgs.runCommand "ProtonUp-Qt-${version}-AppImage" {
        nativeBuildInputs = [ pkgs.squashfsTools pkgs.binutils-unwrapped pkgs.zsync ];
      } ''
        set -euo pipefail
        mkdir -p "$out"
        cd "$out"

        cp ${appimage-runtime} runtime
        chmod u+w runtime
        # Embed the update information into the runtime's reserved .upd_info section
        read -r offset size < <(readelf -SW runtime | awk '$2 == ".upd_info" { print strtonum("0x" $5), strtonum("0x" $6) }')
        [ ${toString (lib.stringLength updateInformation)} -lt "$size" ]
        printf '%s' ${lib.escapeShellArg updateInformation} | dd of=runtime bs=1 seek="$offset" conv=notrunc status=none

        mksquashfs ${appdir} appimage.squashfs -all-root -noappend -comp zstd -Xcompression-level 19 -b 1M -quiet
        cat runtime appimage.squashfs > ${appimageName}
        rm runtime appimage.squashfs
        chmod +x ${appimageName}

        zsyncmake -u ${appimageName} -o ${appimageName}.zsync ${appimageName}
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
