{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "kubeseal-webgui.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kubeseal-webgui.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kubeseal-webgui.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "kubeseal-webgui.labels" -}}
{{- $labels := default (dict) .Values.commonLabels -}}
{{- $_ := set $labels "app" (include "kubeseal-webgui.name" .) -}}
{{- $_ := set $labels "chart" .Chart.Name -}}
{{- $_ := set $labels "release" .Release.Name -}}
{{- $_ := set $labels "heritage" .Release.Service -}}
{{- toYaml $labels -}}
{{- end -}}

{{/*
The path the UI is served under (ingress.path, route.path): "/" or a prefix
like "/kubeseal-webgui", without trailing slash. The UI's nginx only accepts
prefixes made of [A-Za-z0-9._~-] path segments, so anything else fails here
instead of rendering an ingress that cannot work. Also rejected:
- "." and "..": browsers remove them from URLs, so requests would not match
  the prefix;
- prefixes that end like a path the UI's nginx serves itself (an API endpoint
  such as "/config", "/sealed-secrets/<name>", or a UI file such as
  "/assets/<name>"): without the trailing slash such a prefix would reach that
  path instead of being redirected to the start page. Keep this list in step
  with ui/nginx-default.conf.
*/}}
{{- define "kubeseal-webgui.servedPath" -}}
{{- $path := . | default "/" | toString -}}
{{- if ne $path "/" -}}
{{- $path = trimSuffix "/" $path -}}
{{- end -}}
{{- if not (regexMatch "^(/|(/[A-Za-z0-9._~-]+)+)$" $path) -}}
{{- fail (printf "invalid path %q: use \"/\" or a prefix like \"/kubeseal-webgui\" made of the characters A-Z a-z 0-9 . _ ~ -" .) -}}
{{- end -}}
{{- if regexMatch "(^|/)\\.\\.?(/|$)" $path -}}
{{- fail (printf "invalid path %q: \".\" and \"..\" are not allowed as path segments" .) -}}
{{- end -}}
{{- if ne $path "/" -}}
{{- $segments := splitList "/" $path -}}
{{- $last := last $segments -}}
{{- $parent := index $segments (sub (len $segments) 2) -}}
{{- if or (has $last (list "secrets" "namespaces" "config" "docs" "openapi.json" "config.json" "favicon.ico" "favicon.svg" "index.html")) (has $parent (list "sealed-secrets" "assets")) -}}
{{- fail (printf "invalid path %q: it ends like a path the UI serves itself (an API endpoint or a UI file); choose another name, e.g. \"/kubeseal-webgui\"" .) -}}
{{- end -}}
{{- end -}}
{{- $path -}}
{{- end -}}

{{/*
The scope the UI starts with (defaultScope). A typo fails here: the UI would
silently fall back to "strict" instead. Only a missing (null) or empty value
means "strict", like an empty ingress.path means "/"; anything else, false
and 0 included, must be one of the scopes. Keep the list in step with SCOPES
in ui/src/constants.js.
*/}}
{{- define "kubeseal-webgui.defaultScope" -}}
{{- $scope := .Values.defaultScope -}}
{{- if or (kindIs "invalid" $scope) (eq (toString $scope) "") -}}
{{- $scope = "strict" -}}
{{- end -}}
{{- $scope = toString $scope -}}
{{- if not (has $scope (list "strict" "namespace-wide" "cluster-wide")) -}}
{{- fail (printf "invalid defaultScope %q: use \"strict\", \"namespace-wide\" or \"cluster-wide\"" $scope) -}}
{{- end -}}
{{- $scope -}}
{{- end -}}

{{/*
A feature flag of the values (the context) read the way the UI reads
config.json: the spellings of toBoolean() in ui/src/config.js are true, in any
case, everything else is false. A quoted "false" is a non-empty string and
would be true for "if" itself, so chart and UI would disagree. "true", or empty
for false, as "if" expects of an "include".
*/}}
{{- define "kubeseal-webgui.isTrue" -}}
{{- if has (. | toString | lower) (list "true" "1" "yes" "on") -}}
true
{{- end -}}
{{- end -}}

{{/*
Whether the UI lists the namespaces of the cluster (enableNamespaceListing).
*/}}
{{- define "kubeseal-webgui.namespaceListing" -}}
{{- include "kubeseal-webgui.isTrue" .Values.enableNamespaceListing -}}
{{- end -}}

{{/*
Whether the UI may import the keys of existing SealedSecrets
(enableExistingSealedSecretLoading).
*/}}
{{- define "kubeseal-webgui.sealedSecretLoading" -}}
{{- include "kubeseal-webgui.isTrue" .Values.enableExistingSealedSecretLoading -}}
{{- end -}}

{{/*
Whether the chart creates its ClusterRole and ClusterRoleBinding: not for a
custom ServiceAccount, and not when nothing needs cluster-wide read access
(neither the namespace list nor the import of existing SealedSecrets).
*/}}
{{- define "kubeseal-webgui.clusterRbac" -}}
{{- if and (not .Values.customServiceAccountName) (or (include "kubeseal-webgui.namespaceListing" .) (include "kubeseal-webgui.sealedSecretLoading" .)) -}}
true
{{- end -}}
{{- end -}}
