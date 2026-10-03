# AegisOS top-level Makefile. Run `make help`.
SHELL := /bin/bash
VERSION := $(shell cat VERSION)
ISO := dist/AegisOS-$(VERSION)-amd64.iso
PYTHONPATH := packages/aegis-core
export PYTHONPATH

.PHONY: help test test-unit test-shell lint-manifest verify build iso debs clean release

help:
	@echo "AegisOS $(VERSION)"
	@echo "  make test      run unit tests, manifest validation and shell syntax checks"
	@echo "  make verify    static repository verification (scripts/verify.sh)"
	@echo "  make debs      build the Aegis .deb packages into dist/"
	@echo "  make build     build the ISO (needs Debian/live-build + root; see docs/BUILD.md)"
	@echo "  make iso       alias for build"
	@echo "  make release   build ISO + checksums (maintainers)"
	@echo "  make clean     remove build outputs"

test:
	./scripts/test.sh

test-unit:
	python3 -m unittest discover -s tests -t . -v

verify:
	./scripts/verify.sh

debs:
	./scripts/build-debs.sh

build iso:
	./scripts/build.sh

release:
	./scripts/release.sh

clean:
	./scripts/clean.sh
