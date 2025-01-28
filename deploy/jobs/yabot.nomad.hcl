variable "app_image" {
  type = string
}
variable "version" {
  type = string
  default = "2"
}
variable "yabot-data-env" {
  type=string
  default = <<EOH
{{ with secret "secrets/yabot"}}{{range $key, $value := .Data.data}}{{$key}}={{$value | toJSON}}
{{end}}
{{end}}
EOH
}

job "j-yabot-new" {
  datacenters = ["nsk"]
  type        = "service"
  update {
    max_parallel = 1
    health_check = "checks"
    min_healthy_time  = "90s"
    healthy_deadline  = "5m"
    auto_revert       = true
    auto_promote      = true
    canary            = 1
    stagger           = "30s"
  }
  vault {
    policies = ["read"]
  }
  group "g-yabot-new" {
    constraint {
      attribute = "${attr.unique.hostname}"
      operator = "regexp"
      value = "nsk-node-*"
    }
    count = 1

    task "t-yabot-new" {
      driver = "docker"
      meta {
        version = "${var.version}"
      }
      config {
        image = "${var.app_image}"
        force_pull = "true"
      }
      template {
        data = "${var.yabot-data-env}"
        destination = "/local/.env"
        change_mode = "noop"
      }
      resources {
        cpu    = 100
        memory = 512
      }
    }
  }
}
