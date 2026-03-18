{{/*
Expand the name of the chart.
*/}}
{{- define "openstack-vm-name-exporter.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "openstack-vm-name-exporter.fullname" -}}
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
Common labels.
*/}}
{{- define "openstack-vm-name-exporter.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "openstack-vm-name-exporter.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "openstack-vm-name-exporter.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openstack-vm-name-exporter.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
ConfigMap name.
*/}}
{{- define "openstack-vm-name-exporter.configMapName" -}}
{{- printf "%s-env" (include "openstack-vm-name-exporter.fullname" .) -}}
{{- end -}}

{{/*
Secret name.
*/}}
{{- define "openstack-vm-name-exporter.secretName" -}}
{{- if .Values.secret.existingSecret -}}
{{- .Values.secret.existingSecret -}}
{{- else -}}
{{- printf "%s-auth" (include "openstack-vm-name-exporter.fullname" .) -}}
{{- end -}}
{{- end -}}
