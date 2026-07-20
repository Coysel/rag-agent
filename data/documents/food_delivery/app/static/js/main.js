// 星级评分交互
document.addEventListener('DOMContentLoaded', function () {
    const starInputs = document.querySelectorAll('.star-rating-input input');
    if (starInputs.length > 0) {
        starInputs.forEach(input => {
            input.addEventListener('change', function () {
                const stars = this.closest('.star-rating-input').querySelectorAll('label');
                stars.forEach((s, i) => {
                    s.style.color = i < this.value ? '#ffc107' : '#ddd';
                });
            });
        });
    }
});
