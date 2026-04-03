module.exports = {
  apps: [
    {
      name: "fastapi-backend",
      script: "./start.sh",
      cwd: "/home/kcpele/backend",
      env: {
        NODE_ENV: "production",
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
    },
  ],
};
