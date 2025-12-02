// ========================================
// KHUSHBOO JEWELLERS - REFINED FINAL
// ========================================

// ===== HERO CAROUSEL (3 SECONDS AUTO-ROTATION) =====
let currentSlideIndex = 0;
const slides = document.querySelectorAll('.carousel-slide');
const dots = document.querySelectorAll('.dot');
const totalSlides = slides.length;

// Show specific slide
function showSlide(index) {
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    
    if (slides[index]) slides[index].classList.add('active');
    if (dots[index]) dots[index].classList.add('active');
}

// Next slide
function nextSlide() {
    currentSlideIndex = (currentSlideIndex + 1) % totalSlides;
    showSlide(currentSlideIndex);
}

// Go to specific slide
function goToSlide(index) {
    currentSlideIndex = index;
    showSlide(currentSlideIndex);
    resetCarouselTimer();
}

// Auto-rotate every 3 seconds (FASTER)
let carouselTimer = setInterval(nextSlide, 3000);

// Reset timer
function resetCarouselTimer() {
    clearInterval(carouselTimer);
    carouselTimer = setInterval(nextSlide, 3000);
}

// Dot click events
dots.forEach((dot, index) => {
    dot.addEventListener('click', () => goToSlide(index));
});

// ===== HEADER SCROLL EFFECT =====
const header = document.querySelector('.header');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
});

// ===== MOBILE NAVIGATION =====
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        hamburger.classList.toggle('active');
    });

    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            hamburger.classList.remove('active');
        });
    });
}

// ===== SMOOTH SCROLLING =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        
        e.preventDefault();
        const target = document.querySelector(href);
        
        if (target) {
            const headerHeight = 89;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerHeight;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// ===== ACTIVE NAV ON SCROLL =====
function updateActiveNav() {
    const sections = document.querySelectorAll('section[id]');
    const scrollY = window.pageYOffset;

    sections.forEach(section => {
        const sectionHeight = section.offsetHeight;
        const sectionTop = section.offsetTop - 100;
        const sectionId = section.getAttribute('id');
        const navLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

        if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            if (navLink) navLink.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNav);

// ===== CONTACT FORM VALIDATION =====
const contactForm = document.getElementById('contactForm');

if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const name = document.getElementById('name');
        const email = document.getElementById('email');
        const phone = document.getElementById('phone');
        const message = document.getElementById('message');
        
        if (!name || !name.value.trim()) {
            alert('Please enter your name');
            if (name) name.focus();
            return;
        }
        
        if (!email || !email.value.trim()) {
            alert('Please enter your email');
            if (email) email.focus();
            return;
        }
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            alert('Please enter a valid email address');
            email.focus();
            return;
        }
        
        if (!phone || !phone.value.trim()) {
            alert('Please enter your phone number');
            if (phone) phone.focus();
            return;
        }
        
        const cleanPhone = phone.value.replace(/\D/g, '');
        if (cleanPhone.length < 10) {
            alert('Please enter a valid 10-digit phone number');
            phone.focus();
            return;
        }
        
        if (!message || !message.value.trim()) {
            alert('Please enter your message');
            if (message) message.focus();
            return;
        }
        
        alert('Thank you for your interest! We will contact you soon to discuss wholesale partnership opportunities.');
        contactForm.reset();
    });
}

// ===== SCROLL ANIMATIONS =====
function fadeInOnScroll() {
    const elements = document.querySelectorAll('.feature-card, .collection-item, .testimonial-card, .stat-card');
    
    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const elementBottom = element.getBoundingClientRect().bottom;
        
        if (elementTop < window.innerHeight * 0.9 && elementBottom > 0) {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const animatedElements = document.querySelectorAll('.feature-card, .collection-item, .testimonial-card, .stat-card');
    animatedElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });
    
    fadeInOnScroll();
});

window.addEventListener('scroll', fadeInOnScroll);
window.addEventListener('load', fadeInOnScroll);

// ===== STATS COUNTER =====
function animateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    let animated = false;

    function countUp(element, target, suffix = '+') {
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target + suffix;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + suffix;
            }
        }, 16);
    }

    window.addEventListener('scroll', () => {
        if (animated) return;
        
        const statsSection = document.querySelector('.stats-grid');
        if (statsSection) {
            const sectionTop = statsSection.getBoundingClientRect().top;
            
            if (sectionTop < window.innerHeight * 0.75) {
                animated = true;
                statNumbers.forEach(stat => {
                    const text = stat.textContent;
                    let target, suffix;
                    
                    if (text.includes('+')) {
                        target = parseInt(text.replace('+', ''));
                        suffix = '+';
                    } else if (text.includes('%')) {
                        target = parseInt(text.replace('%', ''));
                        suffix = '%';
                    } else if (text.includes('/')) {
                        return;
                    } else {
                        target = parseInt(text);
                        suffix = '';
                    }
                    
                    countUp(stat, target, suffix);
                });
            }
        }
    });
}

animateStats();

// ===== PREVENT FORM RESUBMISSION =====
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

// ===== LAZY LOADING =====
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            }
        });
    });

    const lazyImages = document.querySelectorAll('img[data-src]');
    lazyImages.forEach(img => imageObserver.observe(img));
}

// ===== COLLECTION BADGE PULSE =====
document.addEventListener('DOMContentLoaded', () => {
    const badges = document.querySelectorAll('.collection-badge');
    badges.forEach((badge, index) => {
        setTimeout(() => {
            badge.style.animation = 'pulse 2s ease-in-out infinite';
        }, index * 100);
    });
});

// Add pulse animation
const style = document.createElement('style');
style.textContent = `
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}
`;
document.head.appendChild(style);

// ===== CONSOLE MESSAGE =====
console.log('%c🪙 Khushboo Jewellers', 'color: #B8860B; font-size: 20px; font-weight: bold;');
console.log('%c✨ Odisha\'s Traditional Silver Wholesale Partner', 'color: #666; font-size: 14px;');
console.log('%c📍 Nayasadak, Cuttack | 📞 +91 78735 90001', 'color: #999; font-size: 12px;');