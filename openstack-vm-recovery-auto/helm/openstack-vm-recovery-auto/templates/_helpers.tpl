{{- define "openstack-vm-recovery.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "openstack-vm-recovery.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "openstack-vm-recovery.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "openstack-vm-recovery.labels" -}}
app.kubernetes.io/name: {{ include "openstack-vm-recovery.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "openstack-vm-recovery.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openstack-vm-recovery.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "openstack-vm-recovery.secretName" -}}
{{- if .Values.openstack.secret.name -}}
{{- .Values.openstack.secret.name -}}
{{- else -}}
{{- printf "%s-auth" (include "openstack-vm-recovery.fullname" .) -}}
{{- end -}}
{{- end -}}
