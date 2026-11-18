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
instead of rendering an ingress that cannot work.
*/}}
{{- define "kubeseal-webgui.servedPath" -}}
{{- $path := . | default "/" | toString -}}
{{- if ne $path "/" -}}
{{- $path = trimSuffix "/" $path -}}
{{- end -}}
{{- if not (regexMatch "^(/|(/[A-Za-z0-9._~-]+)+)$" $path) -}}
{{- fail (printf "invalid path %q: use \"/\" or a prefix like \"/kubeseal-webgui\" made of the characters A-Z a-z 0-9 . _ ~ -" .) -}}
{{- end -}}
{{- $path -}}
{{- end -}}
