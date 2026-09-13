---
name: jarvis-laravel
description: Laravel/PHP web application development with Eloquent, Blade, middleware, and modern patterns.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# Laravel Development

## What I do

- Laravel application development
- Eloquent ORM and database design
- Blade templating
- Middleware and authentication
- API development
- Queue jobs and events

## When to use me

Use this skill when working with Laravel, PHP, Eloquent, Blade, or backend API development.

## Patterns

### Eloquent Model
```php
class User extends Model
{
    protected $fillable = ['name', 'email'];
    
    public function posts()
    {
        return $this->hasMany(Post::class);
    }
}
```

### API Resource
```php
class UserResource extends JsonResource
{
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->email,
        ];
    }
}
```

### Middleware
```php
class EnsureWebhookValid
{
    public function handle($request, Closure $next)
    {
        // validation logic
        return $next($request);
    }
}
```

## Anti-patterns

- Don't put business logic in controllers
- Don't skip mass assignment protection
- Don't ignore N+1 query problems

---
*Source: Extracted from wshobson api-scaffolding, backend-development agents*
