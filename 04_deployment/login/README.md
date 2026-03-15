# Authentication Examples for Shiny Apps

This folder contains examples of different authentication approaches for Shiny applications (both Python and R).

## Overview

These examples demonstrate how to add user authentication to Shiny apps, from simple password protection to industry-standard authentication using Supabase.

## Examples

### 1. Simple Password Protection

**`shinypy_password/`** - Python Shiny with basic password gate
- Minimal example for educational purposes
- Single shared password
- **Not for production use** - code is visible to clients

### 2. Supabase Authentication

**`shinypy_supabase/`** - Python Shiny with Supabase email/password authentication
- Industry-standard authentication
- User accounts with email/password
- JWT token-based sessions
- Suitable for production (with proper security practices)

**`shinyr_supabase/`** - R Shiny with Supabase email/password authentication
- Same authentication approach as Python version
- Uses `httr2` for HTTP requests
- REST API integration with Supabase

## Comparison

| Feature | Password Protection | Supabase Authentication |
|---------|-------------------|----------------------|
| **User Management** | Single shared password | Individual user accounts |
| **Security Level** | Minimal (educational only) | Production-ready |
| **Setup Complexity** | Very simple | Medium (requires Supabase account) |
| **Cost** | Free | Free (10,000 users) |
| **Scalability** | Not scalable | Scales to 10K+ users |
| **User Experience** | Basic | Professional |
| **Best For** | Learning, demos | Real applications |

## Quick Start

### Password Protection (Python)

```bash
cd shinypy_password
python -m shiny run app.py
```

### Supabase Authentication

1. **Create Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Get Credentials**: Project URL and public key from Settings > API
3. **Set Environment Variables**:
   ```bash
   export SUPABASE_URL="https://YOUR_PROJECT_ID.supabase.co"
   export SUPABASE_PUBLIC_KEY="your-public-key-here"
   ```
4. **Run the App**:
   ```bash
   # Python
   cd shinypy_supabase
   python -m shiny run app.py
   
   # R
   cd shinyr_supabase
   Rscript -e "shiny::runApp('app.R')"
   ```

## Cost Information

### Supabase Free Tier

- **10,000 monthly active users** - Perfect for learning and small apps
- **No credit card required** to start
- **Unlimited projects** on free tier
- **PostgreSQL database** included
- **Row Level Security (RLS)** for data protection

For most educational and small projects, the free tier is sufficient.

## Key Concepts

### Authentication vs Authorization

- **Authentication**: Verifying who a user is (login)
- **Authorization**: Determining what a user can do (permissions)

Supabase handles authentication. You can add authorization via Row Level Security (RLS) policies.

### JWT Tokens

Supabase uses JSON Web Tokens (JWTs) for session management:
- Tokens contain user information
- Tokens expire for security
- Tokens can be refreshed without re-authentication

### Row Level Security (RLS)

Supabase's RLS allows you to:
- Control data access at the database level
- Create policies based on user identity
- Protect sensitive data automatically

## Security Best Practices

### For Production Apps

1. **Use HTTPS**: Always use HTTPS in production
2. **Environment Variables**: Never hardcode credentials
3. **RLS Policies**: Implement Row Level Security for database access
4. **Token Management**: Handle token expiration and refresh
5. **Input Validation**: Validate all user inputs
6. **Error Handling**: Don't expose sensitive information in error messages

### What's Safe to Expose

- ✅ **Public Key**: Safe for client-side use (RLS protects data)
- ❌ **Service Role Key**: Never expose in client code
- ✅ **Project URL**: Safe to expose
- ❌ **Database Passwords**: Never expose

## Next Steps

### For Learning

1. Start with the password example to understand the basic flow
2. Move to Supabase authentication for real-world patterns
3. Experiment with different authentication methods:
   - OAuth (Google, GitHub, etc.)
   - Magic links (passwordless)
   - Social login

### For Production

1. Set up proper environment variable management
2. Implement Row Level Security policies
3. Add token refresh logic
4. Set up email verification
5. Add password reset functionality
6. Monitor authentication events in Supabase dashboard

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Auth Guide](https://supabase.com/docs/guides/auth)
- [Shiny for Python](https://shiny.posit.co/py/)
- [Shiny for R](https://shiny.rstudio.com/)
- [httr2 Documentation](https://httr2.r-lib.org/)

## Individual Examples

- **[Python Password Example](shinypy_password/README.md)** - Simple password protection
- **[Python Supabase Example](shinypy_supabase/README.md)** - Supabase authentication in Python
- **[R Supabase Example](shinyr_supabase/README.md)** - Supabase authentication in R
