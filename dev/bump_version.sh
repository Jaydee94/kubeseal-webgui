#!/bin/bash

# Check if a version argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

VERSION=$1

# Update the version in pyproject.toml
if [ -f api/pyproject.toml ]; then
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" api/pyproject.toml
    echo "Updated api/pyproject.toml to version $VERSION"
else
    echo "api/pyproject.toml not found!"
fi

# Update the version in package.json
if [ -f ui/package.json ]; then
    sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" ui/package.json
    echo "Updated ui/package.json to version $VERSION"
else
    echo "ui/package.json not found!"
fi

# Update the version and appVersion in Chart.yaml
if [ -f chart/kubeseal-webgui/Chart.yaml ]; then
    sed -i "s/^appVersion: .*/appVersion: $VERSION/" chart/kubeseal-webgui/Chart.yaml
    echo "Updated chart/kubeseal-webgui/Chart.yaml to version $VERSION"
else
    echo "chart/kubeseal-webgui/Chart.yaml not found!"
fi