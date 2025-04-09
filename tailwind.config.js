/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./**/templates/**/*.html",
        "./static/js/**/*.js",
    ],
    theme: {
        extend: {
            fontWeight: {
                light: 300,
                normal: 400,
                medium: 500,
                bold: 700,
                black: 900,
            },
        },
    },
}
